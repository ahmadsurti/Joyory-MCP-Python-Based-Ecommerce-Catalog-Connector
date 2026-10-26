import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
import httpx
from api.index import app


@pytest.fixture(scope="module")
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://joyory-mcp.vercel.app") as c:
        yield c
    await app.close()


@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["mcp_endpoint"] == "/mcp"


@pytest.mark.asyncio
async def test_root_html_endpoint(client):
    resp = await client.get("/", headers={"Accept": "text/html"})
    assert resp.status_code == 200
    assert "<title>Joyory MCP Server</title>" in resp.text


@pytest.mark.asyncio
async def test_root_head_request_for_monitoring(client):
    # UptimeRobot frequently uses HEAD requests
    resp = await client.head("/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_mcp_initialize_and_tools_list(client):
    # Initialize
    init_resp = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        },
    )
    assert init_resp.status_code == 200
    assert "result" in init_resp.text

    # List tools
    tools_resp = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
    )
    assert tools_resp.status_code == 200
    assert "search_products" in tools_resp.text
    assert "get_catalog_overview" in tools_resp.text
