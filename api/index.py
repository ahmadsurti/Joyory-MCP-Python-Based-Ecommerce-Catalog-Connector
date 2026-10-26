"""
Vercel Serverless Function entry point for Joyory MCP Server.

Vercel bundles src/ and config/ alongside this file via vercel.json includeFiles.
We add the bundled src/ directory to sys.path so joyory_mcp is importable.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

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


class LifespanEnsuringASGI:
    """
    Vercel's Python runtime does NOT send ASGI lifespan events (startup/shutdown).
    The MCP StreamableHTTPSessionManager requires its task group to be running
    before it can handle any requests. This wrapper bootstraps the lifespan on the
    very first /mcp request, transparently and thread-safely.
    """

    def __init__(self, inner_app):
        self.inner_app = inner_app
        self._lifespan_task: asyncio.Task | None = None
        self._shutdown_event: asyncio.Event | None = None
        self._started = asyncio.Event()
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_lifespan(self) -> None:
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return

            self._shutdown_event = asyncio.Event()
            started = asyncio.Event()
            is_first = True

            async def receive():
                nonlocal is_first
                if is_first:
                    is_first = False
                    return {"type": "lifespan.startup"}
                await self._shutdown_event.wait()
                return {"type": "lifespan.shutdown"}

            async def send(msg: dict):
                if msg.get("type") == "lifespan.startup.complete":
                    started.set()

            self._lifespan_task = asyncio.create_task(
                self.inner_app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
            )
            await started.wait()
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
        self._initialized = False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.inner_app(scope, receive, send)
            return

        if scope["type"] == "http":
            path = scope.get("path", "")
            if path == "/mcp" or path.startswith("/mcp/"):
                await self._ensure_lifespan()
            await self.inner_app(scope, receive, send)
            return

        await self.inner_app(scope, receive, send)


# This is the ASGI app Vercel's Python runtime invokes per request.
app = LifespanEnsuringASGI(_raw_app)
