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
When deployed to Vercel (or Render):
* **Transport:** Streamable HTTP
* **URL:** `https://your-project.vercel.app/mcp` (or `https://your-deployment.onrender.com/mcp`)
* **Health Check & Monitoring:** `https://your-project.vercel.app/health`

---

## 4. Production Cloud Deployment (Vercel — Recommended)

The repository is configured for serverless deployment on **Vercel**:

### 4.1 Deployment Options
1. **GitHub Integration (Easiest & Automatic CI/CD):**
   * Push your repository to GitHub.
   * Go to [vercel.com/new](https://vercel.com/new) and import the repository.
   * Vercel will automatically detect `vercel.json` and Python runtime via `requirements.txt`.
   * Click **Deploy**.
2. **Vercel CLI:**
   ```bash
   vercel deploy --prod
   ```

### 4.2 Endpoints on Vercel
* **`/mcp`**: The MCP 2.x Streamable HTTP endpoint for AI hosts (Claude, Cursor, ChatGPT, etc.).
* **`/health`**: Instant JSON health check (`200 OK`) responding in <25ms.
* **`/`**: Visual status card in browser or JSON health summary for HTTP clients.

### 4.3 UptimeRobot / Monitoring Setup
* **URL:** `https://your-project.vercel.app/health` (or `https://your-project.vercel.app/`)
* **Monitoring Type:** HTTP(s) or HEAD
* **Interval:** 5 minutes (or 15 minutes)
* **Expected Status:** `200`
*(Note: Do not point UptimeRobot to `/mcp`, as MCP Streamable HTTP opens a persistent SSE connection for GET requests which will time out standard ping bots).*

---

## 5. Render Deployment (Alternative)

For container-based hosting on Render:

### 5.1 Render Service Settings
* **Service Type:** Web Service (Python 3)
* **Environment:** Python
* **Build Command:** `pip install -e .`
* **Start Command:** `python server.py`
* **Health Check Path:** `/health` (or `/`)

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| `[Errno 11002] getaddrinfo failed` | Local workstation DNS resolution timeout (`WSATRY_AGAIN`) | Temporary local network drop. Retry or switch DNS to `1.1.1.1` / `8.8.8.8`. |
| Port 8000 already in use | Previous instance of `server.py` running in background | Terminate old Python PID: `Stop-Process -Name python` or set `MCP_PORT=8001`. |
| Zero products returned for brand | Special characters or spaces in query | Brand normalizer automatically handles this, but verify against `get_catalog_overview()`. |
| Products show 0 ratings | Catalog products are recently added | Normal behavior on Joyory; `rating=None` signifies unreviewed, not bad. |
