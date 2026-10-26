"""
Vercel Serverless Function entry point for Joyory MCP Server.
"""
from __future__ import annotations
import asyncio
import os
import sys
from pathlib import Path

# Add project root and src/ to sys.path
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
for p in (str(_ROOT), str(_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp.server.transport_security import TransportSecuritySettings
from joyory_mcp.server import mcp, _init_adapter

# Ensure adapter is initialized with REST API
_init_adapter()

# Create Starlette app in stateless HTTP mode for serverless environments
# Disable host header DNS-rebinding restrictions so cloud URLs (e.g. *.vercel.app) work seamlessly
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
    ASGI middleware ensuring that the MCP session manager's lifespan task group
    is safely initialized on the first request even if the serverless runtime
    does not trigger ASGI lifespan.startup.
    """

    def __init__(self, inner_app):
        self.inner_app = inner_app
        self._lifespan_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def _ensure_lifespan(self) -> None:
        session_mgr = getattr(mcp._lowlevel_server, "_session_manager", None)
        if session_mgr is not None and getattr(session_mgr, "_task_group", None) is None:
            async with self._lock:
                if getattr(session_mgr, "_task_group", None) is None:
                    started = asyncio.Event()
                    first = True

                    async def receive():
                        nonlocal first
                        if first:
                            first = False
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

    async def close(self) -> None:
        """Clean up the lifespan task."""
        self._shutdown_event.set()
        if self._lifespan_task is not None and not self._lifespan_task.done():
            try:
                await self._lifespan_task
            except Exception:
                pass
        self._lifespan_task = None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            await self.inner_app(scope, receive, send)
            return

        if scope["type"] == "http":
            # Only /mcp requires the MCP session manager task group
            path = scope.get("path", "")
            if path == "/mcp" or path.startswith("/mcp/"):
                await self._ensure_lifespan()
            await self.inner_app(scope, receive, send)
            return

        await self.inner_app(scope, receive, send)


# Expose app for Vercel Python runtime
app = LifespanEnsuringASGI(_raw_app)
