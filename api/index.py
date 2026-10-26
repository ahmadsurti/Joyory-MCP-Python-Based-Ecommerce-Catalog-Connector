"""
Vercel Serverless Function entry point for Joyory MCP Server.

Vercel bundles src/ and config/ alongside this file via vercel.json includeFiles.
We add the bundled src/ directory to sys.path so joyory_mcp is importable.
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode

# Vercel bundles files relative to the function. Add src/ to path.
_HERE = Path(__file__).resolve().parent          # /var/task/api/
_ROOT = _HERE.parent                              # /var/task/
_SRC = _ROOT / "src"

for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Also try the directory alongside this file (Vercel flat-copies includeFiles)
_ALONGSIDE = _HERE / "src"
if _ALONGSIDE.exists() and str(_ALONGSIDE) not in sys.path:
    sys.path.insert(0, str(_ALONGSIDE))

from mcp.server.transport_security import TransportSecuritySettings
from joyory_mcp.server import mcp, _init_adapter

# Initialise adapter once at module load (warm start reuses this)
_init_adapter()

# Starlette ASGI app — stateless_http=True is mandatory for serverless:
# each request gets its own MCP transport; no persistent session state.
# DNS-rebinding protection is disabled so *.vercel.app hosts are accepted.
_raw_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
    ),
)

# ---------------------------------------------------------------------------
# Path recovery
#
# Every public URL is rewritten to /api/index.py, and the ASGI scope then
# carries scope["path"] == "/api/index.py" -- the ORIGINAL path is gone.
# Mapping that to "/" (the old behaviour) sent POST /mcp to the landing-page
# route, which only allows GET/HEAD, hence "405 allow: GET, HEAD".
#
# Fix: each rewrite in vercel.json appends ?route=<logical path> to its
# destination, and we read it back here. If the marker is missing for any
# reason we fall back on the method: GET/HEAD -> "/", anything else -> "/mcp"
# (the landing page can't serve those methods, so they can only be MCP).
# ---------------------------------------------------------------------------
_ENTRY_PATHS = {"/api", "/api/", "/api/index", "/api/index.py"}


def _resolve_route(scope: dict) -> tuple[str, bytes]:
    """Return (logical_path, query_string_without_marker)."""
    path = scope.get("path") or "/"
    method = scope.get("method", "GET").upper()
    raw_qs = scope.get("query_string", b"") or b""

    if path not in _ENTRY_PATHS:
        # Not a Vercel entry path (e.g. local uvicorn): only strip a /api prefix.
        if path.startswith("/api/"):
            path = path[4:]
        return path, raw_qs

    route = None
    rest: list[tuple[str, str]] = []
    for k, v in parse_qsl(raw_qs.decode("latin1"), keep_blank_values=True):
        if k == "route" and route is None:
            route = v
        else:
            rest.append((k, v))
    clean_qs = urlencode(rest).encode("latin1")

    if route is not None:
        route = route.strip("/")
        if route in ("index", "index.py"):
            route = ""
        return "/" + route, clean_qs

    # No marker: decide by method (see comment above).
    return ("/" if method in ("GET", "HEAD") else "/mcp"), clean_qs


class LifespanEnsuringASGI:
    """
    Vercel's Python runtime does NOT send ASGI lifespan events (startup/shutdown).
    The MCP StreamableHTTPSessionManager requires its task group to be running
    before it can handle any requests. This wrapper bootstraps the lifespan on the
    first /mcp request and recovers the original request path from Vercel's rewrite.
    It also handles CORS preflights and direct probes from Claude.ai.
    """

    def __init__(self, inner_app):
        self.inner_app = inner_app
        self._lifespan_task: asyncio.Task | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._lock: asyncio.Lock | None = None   # created lazily, inside the running loop
        self._initialized = False

    @staticmethod
    def _manager():
        return getattr(mcp._lowlevel_server, "_session_manager", None)

    def _running(self) -> bool:
        mgr = self._manager()
        return mgr is not None and getattr(mgr, "_task_group", None) is not None

    async def _ensure_lifespan(self) -> None:
        if self._running():
            return

        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._running():
                return

            # If a previous lifespan task died (e.g. the runtime recycled the
            # event loop between invocations) the manager is stopped but still
            # marked "started", and run() would refuse to start again and hang
            # us here. Its task group is gone, so re-arming it is safe.
            mgr = self._manager()
            if mgr is not None and getattr(mgr, "_has_started", False):
                mgr._has_started = False

            self._shutdown_event = asyncio.Event()
            started = asyncio.Event()
            failure: list[str] = []
            is_first = True

            async def receive():
                nonlocal is_first
                if is_first:
                    is_first = False
                    return {"type": "lifespan.startup"}
                await self._shutdown_event.wait()
                return {"type": "lifespan.shutdown"}

            async def send(msg: dict):
                t = msg.get("type")
                if t == "lifespan.startup.complete":
                    started.set()
                elif t == "lifespan.startup.failed":
                    failure.append(msg.get("message", "lifespan startup failed"))
                    started.set()

            task = asyncio.create_task(
                self.inner_app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
            )
            # If the task dies before signalling, don't wait forever.
            task.add_done_callback(lambda _t: started.set())
            self._lifespan_task = task

            try:
                await asyncio.wait_for(started.wait(), timeout=10)
            except asyncio.TimeoutError:
                task.cancel()
                raise RuntimeError("MCP lifespan did not start within 10s")

            if failure:
                raise RuntimeError(f"MCP lifespan startup failed: {failure[0]}")
            if task.done():
                exc = None if task.cancelled() else task.exception()
                raise RuntimeError(f"MCP lifespan task exited during startup: {exc!r}")
            self._initialized = True

    async def close(self) -> None:
        """Gracefully shut down the bootstrapped lifespan task (used in tests)."""
        if self._shutdown_event is not None:
            self._shutdown_event.set()
        if self._lifespan_task is not None and not self._lifespan_task.done():
            try:
                await self._lifespan_task
            except Exception:
                pass
        self._lifespan_task = None
        self._shutdown_event = None
        self._initialized = False
        mgr = self._manager()
        if mgr is not None:
            mgr._task_group = None

    async def _respond(self, send, status: int, body: bytes, headers=None, head_only=False):
        hdrs = [[b"content-length", str(len(body)).encode()]] + (headers or [])
        await send({"type": "http.response.start", "status": status, "headers": hdrs})
        await send({"type": "http.response.body", "body": b"" if head_only else body, "more_body": False})

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.inner_app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.inner_app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        raw_path = scope.get("path", "")
        raw_qs = scope.get("query_string", b"") or b""

        # Recover the real path BEFORE anything else looks at it.
        path, clean_qs = _resolve_route(scope)

        # Diagnostic endpoint: /debug, or ANY url with ?debug=1 (works even if
        # the rewrite marker is being dropped, since the original query survives).
        if path == "/debug" or b"debug=1" in raw_qs:
            hdrs = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", [])}
            dbg = {
                "scope_path_from_vercel": raw_path,
                "scope_raw_path": (scope.get("raw_path") or b"").decode("latin1", errors="ignore"),
                "scope_query_string": raw_qs.decode("latin1"),
                "resolved_path": path,
                "method": method,
                "headers": hdrs,
            }
            await self._respond(
                send, 200, json.dumps(dbg, indent=2).encode(),
                [[b"content-type", b"application/json"]],
            )
            return

        # Handle CORS preflight for any route
        if method == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": [
                    [b"access-control-allow-origin", b"*"],
                    [b"access-control-allow-methods", b"GET, POST, DELETE, OPTIONS, HEAD"],
                    [b"access-control-allow-headers", b"*"],
                ],
            })
            await send({"type": "http.response.body", "body": b"", "more_body": False})
            return

        # Direct response for GET/HEAD /mcp probe (Claude.ai connector verification)
        if path == "/mcp" and method in ("GET", "HEAD"):
            body = (
                b'{"server":"Joyory Product Catalog MCP","version":"2.0",'
                b'"transport":"streamable-http","protocol":"MCP 2.x","auth":"none",'
                b'"endpoint":"/mcp","methods":["POST","GET","OPTIONS","HEAD"]}'
            )
            await self._respond(
                send, 200, body,
                [[b"content-type", b"application/json"], [b"access-control-allow-origin", b"*"]],
                head_only=(method == "HEAD"),
            )
            return

        # Hand Starlette a scope whose path is the REAL path (copy, don't mutate).
        scope = {**scope, "path": path, "raw_path": path.encode(), "query_string": clean_qs}

        # Ensure lifespan is running for MCP JSON-RPC requests
        if path == "/mcp" or path.startswith("/mcp/"):
            await self._ensure_lifespan()

        await self.inner_app(scope, receive, send)


# This is the ASGI app Vercel's Python runtime invokes per request.
app = LifespanEnsuringASGI(_raw_app)
