# Deployment & Operations Guide
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Target Environments:** Local Workstation (Dev) & Render Cloud (Production)  
**Protocol:** MCP 2.x Streamable HTTP (`/mcp`)  

---

## 1. System Prerequisites

* **Python Runtime:** Python 3.10, 3.11, 3.12, or 3.13.
* **Network Connectivity:** Unrestricted outbound HTTPS access to:
  * `beauty.joyory.com` (REST microservices)
  * `joyory.com` (Main web domain)
  * `res.cloudinary.com` (Product media CDN)
* **Operating Systems:** Windows 10/11, macOS, or Linux (Ubuntu 22.04+).

---

## 2. Local Installation & Execution

### 2.1 Clone & Environment Initialization
```bash
# 1. Clone repository
git clone https://github.com/your-org/joyory-mcp.git
cd joyory-mcp

# 2. Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

# 3. Install package in editable development mode
pip install -e .
```

### 2.2 Configuration Setup
Copy the template configuration:
```bash
cp .env.example .env
```
Ensure configuration keys match your requirements:
```ini
JOYORY_BASE_URL=https://joyory.com
JOYORY_TIMEOUT_SECONDS=20
JOYORY_CACHE_TTL_SECONDS=600
JOYORY_MAX_RESULTS=100
MCP_HOST=127.0.0.1
MCP_PORT=8000
```

### 2.3 Starting the Server
```bash
python server.py
```
*The server will pre-warm catalog and offer caches, then output:*
```
[INFO] Joyory MCP on http://127.0.0.1:8000/mcp
```

---

## 3. Connecting AI Host Clients

### 3.1 Claude Desktop Configuration
Add the connector to your `claude_desktop_config.json`:
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "joyory": {
      "command": "python",
      "args": ["-m", "joyory_mcp.server"],
      "cwd": "C:\\path\\to\\joyory-mcp"
    }
  }
}
```

### 3.2 Claude.ai Web & Remote Hosts (Streamable HTTP)
When deployed to a public URL (or tunneled via Cloudflare/ngrok):
* **Transport:** Streamable HTTP
* **URL:** `https://your-deployment.onrender.com/mcp`

---

## 4. Production Cloud Deployment (Render)

The codebase is engineered specifically for zero-friction deployment to **Render** Web Services:

### 4.1 Render Service Settings
* **Service Type:** Web Service (Python 3)
* **Environment:** Python
* **Build Command:** `pip install -e .`
* **Start Command:** `python server.py`
* **Health Check Path:** `/mcp`

### 4.2 Automated Port & Host Resolution
In `src/joyory_mcp/config.py`, the server automatically detects cloud container environments:
```python
# Automatically binds to 0.0.0.0 when Render sets PORT or RENDER=true
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0" if os.getenv("RENDER") or os.getenv("PORT") else "127.0.0.1")
MCP_PORT: int = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))
```
*No manual IP configuration is required on Render; the app dynamically adopts Render's assigned port.*

---

## 5. Troubleshooting & Operational Diagnostics

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| `[Errno 11002] getaddrinfo failed` | Local workstation DNS resolution timeout (`WSATRY_AGAIN`) | Temporary local network drop. Retry or switch DNS to `1.1.1.1` / `8.8.8.8`. |
| Port 8000 already in use | Previous instance of `server.py` running in background | Terminate old Python PID: `Stop-Process -Name python` or set `MCP_PORT=8001`. |
| Zero products returned for brand | Special characters or spaces in query | Brand normalizer automatically handles this, but verify against `get_catalog_overview()`. |
| Products show 0 ratings | Catalog products are recently added | Normal behavior on Joyory; `rating=None` signifies unreviewed, not bad. |
