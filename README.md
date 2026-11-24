# Lyftr AI Gateway – LLM Chatbot with Key Failover and Response Caching

A resilient, production-ready AI Gateway and multi-turn chatbot built with **FastAPI**, **LiteLLM**, **Google Gemini**, **React 18**, and **SQLite**. The system provides automatic API key failover across multiple Gemini API keys, local response caching, per-message token tracking, and persistent session storage.

---

## Table of Contents
- [1. Live URLs](#1-live-urls)
- [2. Run locally](#2-run-locally)
  - [A. Using Docker](#a-using-docker)
  - [B. Without Docker](#b-without-docker)
  - [Environment Variables Reference](#environment-variables-reference)
- [3. Design decisions](#3-design-decisions)
  - [Key Failover Architecture](#key-failover)
  - [Response Caching](#response-caching)
  - [SQLite Session Storage](#sqlite-session-storage)
  - [Request Lifecycle & Architecture](#request-lifecycle--architecture)
  - [Architectural Trade-offs](#architectural-trade-offs)
- [4. Verification](#4-verification)
  - [Health Check (`GET /health`)](#1-backend-health-verification)
  - [Chat Inference (`POST /chat`)](#2-chat-functionality-verification)
  - [Session History (`GET /sessions/{session_id}/messages`)](#3-session-history-verification)
  - [Key Failover Simulation](#4-key-failover-verification)
  - [Response Cache Hits & Misses](#5-response-cache-verification)
  - [Token Usage Tracking](#6-token-usage-tracking-verification)
  - [Automated Test Suite & Frontend Build](#7-automated-test-suite--frontend-build)
- [5. Setup Used](#5-setup-used)
- [6. Bonus features (if any)](#6-bonus-features-if-any)

---

## 1. Live URLs

The application is deployed across cloud infrastructure with separated frontend and backend services:

| Component | Platform | URL |
| :--- | :--- | :--- |
| **Frontend UI** | Vercel | https://lyftr-ai-gateway.vercel.app |
| **Backend API** | Railway | https://lyftr-ai-gateway-production.up.railway.app |
| **Health Endpoint** | Railway | https://lyftr-ai-gateway-production.up.railway.app/health |
| **API Docs (Swagger)** | Railway | https://lyftr-ai-gateway-production.up.railway.app/docs |
| **GitHub Repository** | GitHub | https://github.com/abhinavdwivedi05/lyftr-ai-gateway |

---

## 2. Run locally

### A. Using Docker

Docker Compose runs both the backend (FastAPI) and frontend (React via Nginx) containers with a shared network and a persistent named volume for SQLite.

#### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (WSL2 engine on Windows, or native Docker on Linux/macOS).
- Git installed.

#### 2. Clone Repository
```bash
git clone https://github.com/abhinavdwivedi05/lyftr-ai-gateway.git
cd lyftr-ai-gateway
```

#### 3. Environment Variable Setup
Copy the sample environment file to `.env`:
```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Open `.env` and provide your real Google Gemini API keys from [Google AI Studio](https://aistudio.google.com/):
```env
LLM_API_KEYS=AIzaSyYourFirstKeyHere,AIzaSyYourSecondKeyHere
LLM_MODEL=gemini/gemini-flash-lite-latest
DATABASE_URL=sqlite:////data/app.db
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENABLE_FAILURE_SIMULATION=true
MOCK_LLM=false
```
> [!IMPORTANT]
> Never commit `.env` or expose API keys. The project `.gitignore` excludes `.env` by default.

#### 4. Docker Compose Commands
Build and start all containers in detached mode:
```bash
# Using Makefile
make up

# Direct Docker Compose command
docker compose up --build -d
```

Check running container status:
```bash
# Using Makefile
make status

# Direct Docker Compose command
docker compose ps
```

View container logs in real time:
```bash
# Using Makefile
make logs

# Direct Docker Compose command
docker compose logs -f
```

#### 5. How to Access Frontend and Backend
- **Frontend Web UI**: Open [http://localhost:3000](http://localhost:3000) in your browser.
- **Backend API**: Accessible at [http://localhost:8000](http://localhost:8000).
- **Interactive Swagger Documentation**: Open [http://localhost:8000/docs](http://localhost:8000/docs).
- **Direct Nginx Reverse Proxy**: Port 3000 also proxies API routes directly (`http://localhost:3000/health`, `http://localhost:3000/chat`, `http://localhost:3000/sessions/`).

#### 6. How to Stop Containers
```bash
# Using Makefile
make down

# Direct Docker Compose command
docker compose down
```
*(SQLite data at `/data/app.db` is safely preserved in the named Docker volume `lyftr_sqlite_data`).*

---

### B. Without Docker

You can run the backend and frontend directly on your host machine for local development.

#### 1. Prerequisites
- Python 3.12+ installed.
- Node.js v20+ and npm installed.

#### 2. Python Virtual Environment Setup & Backend Installation
From the repository root:
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

#### 3. Backend Startup Command
Configure `.env` in the project root:
```env
LLM_API_KEYS=your_first_key,your_second_key
LLM_MODEL=gemini/gemini-flash-lite-latest
DATABASE_URL=sqlite:///./data/app.db
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENABLE_FAILURE_SIMULATION=true
MOCK_LLM=false
```

Start the FastAPI application with Uvicorn on port 8000:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```
The server will create the local `./data/` directory and initialize SQLite tables automatically.

#### 4. Frontend Dependencies Installation & Startup
In a separate terminal window, navigate to the frontend directory:
```bash
cd frontend
npm install
```

Start the Vite development server on port 3000:
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

#### 5. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `LLM_API_KEYS` | `placeholder_key_1,placeholder_key_2` | Comma-separated list of Gemini API keys (at least 2 required). |
| `LLM_MODEL` | `gemini/gemini-flash-lite-latest` | LiteLLM model identifier used for Gemini completions. |
| `DATABASE_URL` | `sqlite:////data/app.db` | SQLAlchemy connection string. In Docker: `/data/app.db`; locally: `sqlite:///./data/app.db`. |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed CORS origins. |
| `ENABLE_FAILURE_SIMULATION` | `true` | Enables or disables the `X-Simulate-Failure` header hook. |
| `MOCK_LLM` | `false` | When `true`, returns deterministic mock completions for offline testing without hitting live APIs. |
| `VITE_API_BASE_URL` | `""` (defaults to relative or `http://localhost:8000`) | Frontend environment variable specifying the backend API host. |

---

## 3. Design decisions

### Key Failover

The gateway ensures high availability across rate limits and service outages by managing an ordered key pool with automated failover:

```
[Incoming Request]
        │
        ▼
   [Key 1: key_1] ──(HTTP 429 / 5xx / Quota Error)──► [Fallback Attempt 1]
        │                                                     │
   (Success 200)                                              ▼
        │                                              [Key 2: key_2]
        │                                                     │
        ▼                                                (Success 200)
[Return Live Response]                                        │
  metadata.key_id: "key_1"                                    ▼
  fallback_attempts: 0                               [Return Live Response]
                                                       metadata.key_id: "key_2"
                                                       fallback_attempts: 1
```

- **Configuration & Selection**:
  The gateway reads `LLM_API_KEYS` from the environment, splits by comma, and cleans surrounding quotes and whitespace. Keys are mapped to indexed identifiers (`key_1`, `key_2`, ..., `key_N`). Requests always attempt `key_1` first.
- **Failover Triggering**:
  Any error caught during inference is evaluated by `is_failover_error()`. Failover is triggered on:
  - HTTP Status Codes: `429` (Too Many Requests), `500` (Internal Server Error), `502` (Bad Gateway), `503` (Service Unavailable), and `504` (Gateway Timeout).
  - LiteLLM Exception Types: `RateLimitError`, `InternalServerError`, `BadGatewayError`, `ServiceUnavailableError`, `APIConnectionError`, and `Timeout`.
  - Provider Error Substrings: `quota`, `resource has been exhausted`, `rate limit`, `overloaded`, `connection error`.
- **Secret Redaction**:
  Exceptions are sanitized using regex (`sanitize_error()`), stripping raw Google keys (`AIza...`, `AQ...`), URL query parameters (`?key=...`), and headers before logging. API keys are never output to console logs or HTTP responses.
- **Exhaustion Handling**:
  If all configured keys in the pool fail, the gateway logs a sanitized summary and raises a clean HTTP 503 JSON exception (`{"detail": "all providers unavailable"}`) without exposing Python stack traces.
- **Failure Simulation (`X-Simulate-Failure`)**:
  When `ENABLE_FAILURE_SIMULATION=true`, evaluators can test failover deterministically by sending the `X-Simulate-Failure` header:
  - `key_1=429`: Simulates HTTP 429 on `key_1`. Execution advances immediately to `key_2`, returning `metadata.key_id = "key_2"` and `metadata.fallback_attempts = 1`.
  - `key_1=500`: Simulates server error on `key_1`, successfully failing over to `key_2`.
  - `key_1=429,key_2=500`: Simulates failure on both keys, exhausting the pool and returning HTTP 503.
  - `*=429`: Wildcard failure triggering HTTP 503 across all keys.
  - `key_1=504`: Simulates an upstream gateway timeout on `key_1`.
  
  When simulation is active, the request explicitly passes `caching=False` and `cache={"no-store": True, "no-cache": True}` to LiteLLM. This ensures that test failure requests bypass pre-existing cached responses and never corrupt the cache with simulated test errors.

---

### Response Caching

The gateway integrates LiteLLM's native caching mechanism to eliminate redundant inference costs and provide sub-10ms responses:

- **Implementation**:
  Configured in `app/services/cache_service.py` via `litellm.caching.Cache(type="local")` with `litellm.enable_cache()`. LiteLLM's local in-memory cache stores responses directly in server memory.
- **Cache Key Generation**:
  The cache key is computed deterministically from:
  1. The exact model identifier (e.g. `gemini/gemini-flash-lite-latest`).
  2. The exact sequence of messages including role and content (`system`, prior multi-turn `user`/`assistant` history, and current `user` prompt).
  Two requests in different sessions with identical message sequences hit the exact same cache entry.
- **Cache Hit Behavior**:
  - Response time drops from ~1,000–3,000 ms (live Gemini call) to < 10 ms.
  - Metadata contract: `resolution_source` is set to `"LLM_CACHE"`, `key_id` is set to `null`, and `fallback_attempts` is reset to `0`.
  - Cached token usage (`input_tokens`, `output_tokens`) from the original inference is preserved and reported accurately.
- **Cache Miss Behavior**:
  The request performs live inference, records `resolution_source = "LIVE_INFERENCE"`, reports the responding `key_id` (e.g. `"key_1"`), and stores the result in cache for subsequent matching requests.

---

### SQLite Session Storage

- **Session Management**:
  Session IDs are client-generated strings (e.g. `s-abc1234` or custom identifier) validated to be between 1 and 128 characters.
- **Schema & Persistence**:
  Persisted via SQLAlchemy declarative model in the `messages` table:
  ```sql
  CREATE TABLE messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      metadata TEXT,
      created_at TEXT NOT NULL
  );
  CREATE INDEX ix_messages_session_id ON messages (session_id);
  ```
- **Context Maintenance**:
  On each `POST /chat`, the backend queries `messages` for all records matching `session_id` ordered chronologically (`id ASC`). It appends the optional `system_prompt` (if provided) followed by all previous messages and the current user query, providing complete multi-turn conversation memory to the model.
- **Transaction Safety & State Separation**:
  Database writes occur **only after** successful LLM completion. Both user and assistant records are committed in a single atomic database transaction. If an inference fails (e.g. HTTP 503 all providers down), no messages are written to the database.
- **System Prompt Isolation**:
  System prompts steer inference but are intentionally excluded from `GET /sessions/{session_id}/messages` per the assignment specification.
- **Docker Named Volume**:
  In Docker, the database path is configured as `sqlite:////data/app.db`. Docker Compose mounts the named volume `lyftr_sqlite_data` to `/data`, ensuring database records persist across container restarts, stops, and rebuilds.

---

### Request Lifecycle & Architecture

```
[Client / React UI]
        │
        │ HTTP POST /chat (session_id, message, system_prompt, X-Simulate-Failure)
        ▼
   [Nginx (Port 3000)]  ─── Reverse Proxy ───►  [FastAPI Backend (Port 8000)]
                                                         │
                                               [1. Query History]
                                                         │
                                                         ▼
                                               [SQLite: messages table]
                                                         │
                                               [2. Build Message List]
                                                         │
                                                         ▼
                                            [3. FailoverService.execute]
                                                         │
                                         ┌───────────────┴───────────────┐
                                  [Cache Hit?]                    [Cache Miss]
                                         │                               │
                                   Yes ──┘                               ▼
                                  (Return)                     [Try key_1 via LiteLLM]
                                                                         │
                                                                   Fail? │ (429/5xx)
                                                                         ▼
                                                               [Fallback to key_2]
                                                                         │
                                                                 Success?│ (200 OK)
                                                                         ▼
                                                            [4. Atomic DB Commit]
                                                               User + Assistant
                                                                         │
                                                                         ▼
                                                            [5. Return JSON Response]
                                                               reply + metadata
```

---

### Architectural Trade-offs

1. **LiteLLM In-Memory Local Cache vs. Redis**:
   - *Decision*: In-memory cache using LiteLLM's native `Cache(type="local")`.
   - *Rationale*: Eliminates external service dependencies, reduces operational complexity, runs natively in zero-network Docker test environments, and provides microsecond cache lookups.
   - *Trade-off*: Cache is local to the container process and resets on application restart.
2. **SQLite with Named Volume vs. PostgreSQL**:
   - *Decision*: Single-file SQLite database placed on a persistent Docker named volume (`lyftr_sqlite_data`).
   - *Rationale*: Zero-configuration setup, fast read/write for single-instance workloads, fully self-contained in Docker.
   - *Trade-off*: SQLite does not support horizontal multi-node write clustering, which is suitable for this assignment scope.
3. **Sequential Failover vs. Weighted Load Balancing**:
   - *Decision*: Deterministic sequential failover (`key_1` &rarr; `key_2`).
   - *Rationale*: Guarantees predictable key usage, simplifies verification of primary key preference, and allows unambiguous failure simulation testing.

---

## 4. Verification

### 1. Backend Health Verification

Check database connectivity, configured key count, and caching status.

**Command (PowerShell):**
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Method Get
```

**Command (cURL):**
```bash
curl -s http://localhost:8000/health
```

**Verified Response (HTTP 200):**
```json
{
  "status": "ok",
  "keys_configured": 2,
  "cache_enabled": true
}
```

---

### 2. Chat Functionality Verification

Send a user message to `POST /chat` and receive live model inference.

**Command (PowerShell):**
```powershell
$body = @{ session_id = "verify-chat-1"; message = "What is the capital of France? Answer in one word." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 4
```

**Verified Response (HTTP 200):**
```json
{
  "session_id": "verify-chat-1",
  "reply": "Paris.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-flash-lite-latest",
    "latency_ms": 1842,
    "input_tokens": 17,
    "output_tokens": 2,
    "key_id": "key_1",
    "fallback_attempts": 0
  }
}
```

---

### 3. Session History Verification

Retrieve stored conversation history from SQLite for a session.

**Command (PowerShell):**
```powershell
Invoke-RestMethod -Uri http://localhost:8000/sessions/verify-chat-1/messages -Method Get | ConvertTo-Json -Depth 4
```

**Verified Response (HTTP 200):**
```json
{
  "session_id": "verify-chat-1",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France? Answer in one word."
    },
    {
      "role": "assistant",
      "content": "Paris.",
      "metadata": {
        "resolution_source": "LIVE_INFERENCE",
        "input_tokens": 17,
        "output_tokens": 2
      }
    }
  ]
}
```

---

### 4. Key Failover Verification

#### A. Failover to Key 2 (`key_1=429`)
Simulate HTTP 429 rate limit on `key_1`. The gateway falls back to `key_2`.

**Command (PowerShell):**
```powershell
$body = @{ session_id = "verify-failover-1"; message = "Tell me what 2+2 is in one word." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Headers @{"X-Simulate-Failure"="key_1=429"} -Body $body | ConvertTo-Json -Depth 4
```

**Verified Response (HTTP 200):**
```json
{
  "session_id": "verify-failover-1",
  "reply": "Four.",
  "metadata": {
    "resolution_source": "LIVE_INFERENCE",
    "model": "gemini/gemini-flash-lite-latest",
    "latency_ms": 2274,
    "input_tokens": 13,
    "output_tokens": 2,
    "key_id": "key_2",
    "fallback_attempts": 1
  }
}
```

#### B. All Keys Failing (`*=429`)
Simulate failure across all keys. The gateway returns HTTP 503.

**Command (PowerShell):**
```powershell
$body = @{ session_id = "verify-failover-exhaust"; message = "Fail all keys" } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Headers @{"X-Simulate-Failure"="*=429"} -Body $body
} catch {
  $stream = $_.Exception.Response.GetResponseStream()
  $reader = New-Object System.IO.StreamReader($stream)
  Write-Output "HTTP Status: $($_.Exception.Response.StatusCode.value__) Response: $($reader.ReadToEnd())"
}
```

**Verified Response (HTTP 503):**
```json
HTTP Status: 503 Response: {"detail":"all providers unavailable"}
```

---

### 5. Response Cache Verification

#### Step 1: Initial Request (Cache Miss)
Send a unique query in a new session:
```powershell
$body = @{ session_id = "cache-test-sess-1"; message = "What is the boiling point of water in Celsius? Answer in one word." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 4
```
*Result: `resolution_source: "LIVE_INFERENCE"`, `latency_ms: ~1800`, `key_id: "key_1"`.*

#### Step 2: Identical Request in New Session (Cache Hit)
Send the exact same query in a different session:
```powershell
$body = @{ session_id = "cache-test-sess-2"; message = "What is the boiling point of water in Celsius? Answer in one word." } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 4
```

**Verified Response (HTTP 200):**
```json
{
  "session_id": "cache-test-sess-2",
  "reply": "100°C.",
  "metadata": {
    "resolution_source": "LLM_CACHE",
    "model": "gemini/gemini-flash-lite-latest",
    "latency_ms": 4,
    "input_tokens": 19,
    "output_tokens": 3,
    "key_id": null,
    "fallback_attempts": 0
  }
}
```
*Notice: `resolution_source` is `"LLM_CACHE"`, latency dropped to 4 ms, `key_id` is `null`, `fallback_attempts` is `0`, and cached token counts are preserved.*

---

### 6. Token Usage Tracking Verification

Every chat response contains real, non-zero token metrics returned by the Gemini provider:
- `input_tokens`: Prompt tokens consumed by system prompt, history, and message.
- `output_tokens`: Completion tokens generated by the model.

Both live inference and cached responses return integer token metrics $\ge 1$.

---

### 7. Automated Test Suite & Frontend Build

#### Run All 34 Backend Automated Tests
Execute the comprehensive test suite inside the backend container:
```bash
# Using Makefile
make test

# Or direct Docker Compose command
docker compose exec -e MOCK_LLM=true -T backend pytest tests/ -v
```

**Verified Test Output:**
```text
============================= test session starts ==============================
platform linux -- Python 3.12.16, pytest-9.2.0, pluggy-1.7.0 -- /usr/local/bin/python3.12
collected 34 items

tests/test_health.py::test_health_endpoint PASSED                        [  2%]
tests/test_phase2_endpoints.py::test_1_health_endpoint PASSED            [  5%]
tests/test_phase2_endpoints.py::test_2_successful_chat PASSED            [  8%]
tests/test_phase2_endpoints.py::test_3_empty_message_returns_422 PASSED  [ 11%]
tests/test_phase2_endpoints.py::test_4_message_exceeding_4000_chars_returns_422 PASSED [ 14%]
tests/test_phase2_endpoints.py::test_5_session_history_retrieval PASSED  [ 17%]
tests/test_phase2_endpoints.py::test_6_history_ordering PASSED           [ 20%]
tests/test_phase2_endpoints.py::test_7_unknown_session_returns_404 PASSED [ 23%]
tests/test_phase2_endpoints.py::test_8_assistant_metadata_persistence PASSED [ 26%]
tests/test_phase2_endpoints.py::test_9_session_isolation PASSED          [ 29%]
tests/test_phase2_endpoints.py::test_10_database_persistence_after_reopening_connection PASSED [ 32%]
tests/test_phase3_failover_caching.py::test_1_live_inference_success PASSED [ 35%]
tests/test_phase3_failover_caching.py::test_2_first_request_cache_miss PASSED [ 38%]
tests/test_phase3_failover_caching.py::test_3_identical_request_cache_hit PASSED [ 41%]
tests/test_phase3_failover_caching.py::test_4_identical_response_text PASSED [ 44%]
tests/test_phase3_failover_caching.py::test_5_cache_hit_key_id_is_null PASSED [ 47%]
tests/test_phase3_failover_caching.py::test_6_cache_hit_fallback_attempts_equals_zero PASSED [ 50%]
tests/test_phase3_failover_caching.py::test_7_correct_input_token_tracking PASSED [ 52%]
tests/test_phase3_failover_caching.py::test_8_correct_output_token_tracking PASSED [ 55%]
tests/test_phase3_failover_caching.py::test_9_key_1_429_falls_back_to_key_2 PASSED [ 58%]
tests/test_phase3_failover_caching.py::test_10_key_1_500_falls_back_to_key_2 PASSED [ 61%]
tests/test_phase3_failover_caching.py::test_11_key1_429_key2_500_returns_503 PASSED [ 64%]
tests/test_phase3_failover_caching.py::test_12_wildcard_429_returns_503 PASSED [ 67%]
tests/test_phase3_failover_caching.py::test_13_failed_requests_do_not_enter_history PASSED [ 70%]
tests/test_phase3_failover_caching.py::test_14_cache_is_bypassed_for_simulated_failure_requests PASSED [ 73%]
tests/test_phase3_failover_caching.py::test_15_simulation_is_disabled_when_configured_false PASSED [ 76%]
tests/test_phase3_failover_caching.py::test_16_different_messages_do_not_incorrectly_share_cache PASSED [ 79%]
tests/test_phase3_failover_caching.py::test_17_normal_cache_behavior_works_after_failure_simulation PASSED [ 82%]
tests/test_phase3_failover_caching.py::test_18_key1_simulated_429_followed_by_successful_key2_inference PASSED [ 85%]
tests/test_phase3_failover_caching.py::test_19_both_keys_failing_simulation_returns_503 PASSED [ 88%]
tests/test_phase3_failover_caching.py::test_20_key1_succeeding_without_fallback PASSED [ 91%]
tests/test_phase3_failover_caching.py::test_21_sanitize_error_redacts_api_keys_and_patterns PASSED [ 94%]
tests/test_phase3_failover_caching.py::test_22_real_exception_on_key1_falls_back_to_key2 PASSED [ 97%]
tests/test_phase3_failover_caching.py::test_23_status_504_gateway_timeout_triggers_fallback PASSED [100%]

======================= 34 passed, 14 warnings in 7.80s ========================
```

#### Run Frontend Production Build
```bash
cd frontend
npm run build
```

**Verified Build Output:**
```text
vite v6.1.0 building for production...
transforming...
✓ 1592 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.53 kB │ gzip:  0.35 kB
dist/assets/index-BxOs19_Q.css   16.41 kB │ gzip:  4.02 kB
dist/assets/index-hVvbMcII.js   165.73 kB │ gzip: 52.46 kB
✓ built in 7.97s
```

---

## 5. Setup Used

The application was designed, implemented, and verified using the following confirmed development environment:

- **Operating System**: Windows 11 Home / Pro (x86_64, Windows PowerShell 5.1 & PowerShell Core 7).
- **Primary IDE & AI Assistant**: Cursor IDE with autonomous agent mode.
- **Backend Stack**:
  - Python: `3.12` (Container image: `python:3.12-slim`).
  - Web Framework: FastAPI `>=0.115.0`.
  - ASGI Server: Uvicorn `0.32.0`.
  - Validation: Pydantic `2.9.0` and `pydantic-settings 2.5.0`.
  - ORM & Database Driver: SQLAlchemy `2.0.35` with SQLite 3.
  - LLM Interface: LiteLLM `>=1.52.0`.
  - Additional Runtime Libraries: `orjson 3.10.0`, `soundfile 0.12.0`, `libsndfile1`.
  - Testing Framework: Pytest `8.3.0` with `pytest-asyncio 0.24.0` and `httpx 0.27.2`.
- **Frontend Stack**:
  - Node.js Runtime: `Node.js 22` (Container image: `node:22-alpine`).
  - Library: React `18.3.1` and `react-dom 18.3.1`.
  - Build Tool: Vite `6.1.0` with `@vitejs/plugin-react 4.3.4`.
  - Styling: Tailwind CSS `3.4.17` with PostCSS `8.5.1` and Autoprefixer `10.4.20`.
  - Icons: Lucide React `0.475.0`.
  - Production Web Server: Nginx Alpine (`nginx:alpine`).
- **Containerization & Orchestration**:
  - Docker Desktop v29.x with WSL2 Linux backend integration.
  - Docker Compose v2.
  - Multi-stage Dockerfiles for both services.
- **Version Control & Repository**:
  - Git version control.
  - GitHub Repository: [https://github.com/abhinavdwivedi05/lyftr-ai-gateway](https://github.com/abhinavdwivedi05/lyftr-ai-gateway).
- **Cloud Deployment Platforms**:
  - **Railway**: Hosts the backend FastAPI container connected to a persistent 1GB storage volume mounted at `/data`.
  - **Vercel**: Hosts the production React SPA bundle connected to the Railway backend via `VITE_API_BASE_URL`.

---

## 6. Bonus features (if any)

The following features were implemented beyond the base assignment requirements to enhance usability and production reliability:

1. **Interactive In-Browser Failure Simulation**:
   - *Implementation*: A collapsible **Config** drawer in [`frontend/src/components/Header.jsx`](file:///c:/Users/abhin/Downloads/lyftr_ai_chatbot/frontend/src/components/Header.jsx).
   - *Value*: Allows evaluators to test failover scenarios (`key_1=429`, `key_1=500`, `key_1=429,key_2=500`, and `*=429`) directly from the web interface without writing cURL commands or using external API clients.
2. **Nginx Reverse-Proxy Integration**:
   - *Implementation*: Configured in [`frontend/nginx.conf`](file:///c:/Users/abhin/Downloads/lyftr_ai_chatbot/frontend/nginx.conf).
   - *Value*: In Docker, Nginx serves static assets on port 3000 and reverse-proxies `/health`, `/chat`, and `/sessions/` directly to `backend:8000`. This allows the web UI to make clean relative calls (`/chat`) without CORS preflight latency.
3. **Real-Time Key Pool & Cache Status Pill**:
   - *Implementation*: Dynamically fetched on frontend mount from `GET /health`.
   - *Value*: The header visually displays the live count of configured keys (`2 Keys`) and caching status (`Cache ON` with a green indicator), providing instant transparency into backend connectivity.
4. **Secret-Sanitized Exception Logging**:
   - *Implementation*: `FailoverService.sanitize_error()` in [`backend/app/services/failover_service.py`](file:///c:/Users/abhin/Downloads/lyftr_ai_chatbot/backend/app/services/failover_service.py).
   - *Value*: Automatically detects and redacts Google API keys (`AIza...`, `AQ...`), query parameters, and authorization headers in error logs, preventing credential leakage in production logging services (such as Railway or CloudWatch).
