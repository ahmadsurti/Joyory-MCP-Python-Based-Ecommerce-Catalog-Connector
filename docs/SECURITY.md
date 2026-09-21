# Security Architecture & Threat Analysis
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Classification:** Public / Open Source Prototype  
**Scope:** `src/joyory_mcp/`  

---

## 1. Security Posture & Guiding Principles

The Joyory MCP Connector operates under a **Zero-Trust, Zero-State, Read-Only** architecture. By strictly scoping the product to public catalog discovery, the system dramatically reduces the enterprise attack surface:
* **No Authentication Storage:** The system stores zero passwords, session tokens, JWTs, or customer credentials.
* **No Payment Data:** No credit card, UPI, or financial transactions pass through or terminate within the MCP server.
* **No Persistent Data Stores:** Zero local databases (SQL or NoSQL); runtime memory contains only short-lived catalog cache entries.

---

## 2. Implemented Security Controls

### 2.1 Egress Network Control & Whitelisting (`src/joyory_mcp/config.py`)
To prevent Server-Side Request Forgery (SSRF) and malicious redirect exploitation, outbound HTTP requests are restricted strictly to verified hostnames:
```python
ALLOWED_HOSTS: set[str] = {
    "joyory.com",
    "www.joyory.com",
    "beauty.joyory.com",
    "res.cloudinary.com",
}
```
Any attempt to redirect requests to internal network interfaces (e.g. `169.254.169.254` AWS metadata or local loopback interfaces) is rejected.

### 2.2 Input Sanitization & URL Validation (`src/joyory_mcp/normalize.py`)
* **Strict URL Validation:** The `validate_url()` function strictly verifies that every product and image link uses valid `http` or `https` schemes with authorized hostnames before emission to the host client.
* **HTML Stripping:** Raw API fields containing HTML markup (such as product descriptions and ingredient blurbs) are stripped of all script and HTML tags using regex patterns (`re.sub(r'<[^>]+>', '', text)`), neutralizing client-side injection (XSS) risks.
* **Batch Truncation & Resource Protection:** `tools/details.py` enforces a strict ceiling of 5 product IDs per invocation. Excessive IDs are rejected with advisory warnings, preventing algorithmic denial of service.

### 2.3 Error Obfuscation & Leakage Prevention (`src/joyory_mcp/errors.py`)
Internal system exceptions (e.g., database connection errors, tracebacks, raw HTTP status messages) are intercepted by `friendly_message()`. The server emits sanitized domain error strings (e.g., *"Joyory is currently receiving high traffic"*) rather than leaking internal stack traces or environment variables to the AI client.

### 2.4 Upstream Politeness & Denial of Service Protection (`src/joyory_mcp/cache.py`)
* **In-Memory TTL Caching (600s):** Protects Joyory’s upstream microservices from request floods. Repeated queries for popular terms ("sunscreen", "lipstick") resolve directly from RAM without initiating upstream network traffic.
* **Thread-Safe Locks:** Concurrency locks prevent cache stampede attacks where multiple simultaneous threads attempt to refresh the same expired key simultaneously.

---

## 3. Threat Model (STRIDE Assessment)

| Threat Category | Potential Risk | Implemented Mitigation | Residual Risk Tier |
|---|---|---|---|
| **Spoofing** | Attacker impersonates Joyory API | Enforce HTTPS with strict TLS certificate validation via `httpx`. | Low |
| **Tampering** | In-flight manipulation of catalog responses | End-to-end TLS encryption; Pydantic V2 schema validation on ingestion. | Very Low |
| **Repudiation** | Disputes over read actions | All operations are read-only; no user-mutating transactions occur. | None |
| **Information Disclosure** | Leakage of server environment or internal IPs | `friendly_message()` intercepts stack traces; zero PII ingested. | Very Low |
| **Denial of Service** | Flooding MCP server with search requests | In-memory `TTLCache` (10-min TTL); strict connection timeouts (20s). | Low |
| **Elevation of Privilege** | Remote code execution via tool arguments | Fully parameterized queries; zero `eval()`, `exec()`, or subshell execution. | Zero |

---

## 4. Recommended Future Security Controls (Production Roadmap)

1. **Client API Key Authentication:** For multi-tenant cloud deployments, introduce bearer token authorization at the `/mcp` HTTP reverse-proxy layer to gate unauthorized external access.
2. **Dynamic Host Rate Limiting:** Implement token-bucket rate limiting per client IP (e.g., via Redis or Render API gateway) to mitigate scraping abuse.
3. **Automated Dependency Vulnerability Audits:** Integrate GitHub Dependabot and automated `pip-audit` scans into the CI/CD pipeline to detect CVEs in third-party Python wheels.
