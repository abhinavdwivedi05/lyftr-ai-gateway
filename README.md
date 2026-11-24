# Lyftr AI - LLM Chatbot with Key Failover and Response Caching

Production-ready full-stack AI application featuring Google Gemini model integration via LiteLLM, multi-key automatic failover, response caching, and persistent SQLite session storage.

---

## 1. Live URLs

| Service | Target Platform | Live URL | Status |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vercel | `https://lyftr-ai-chatbot.vercel.app` *(or your deployed Vercel URL)* | Pending User Deployment |
| **Backend API** | Render | `https://lyftr-backend.onrender.com` *(or your deployed Render URL)* | Pending User Deployment |
| **API Docs (Swagger)** | Render | `https://lyftr-backend.onrender.com/docs` | Pending User Deployment |

> **Note on Live Deployment**: In accordance with the assignment guidelines, live URLs are activated as soon as the deployment steps in Section 2 are triggered with your Render and Vercel accounts. No simulated or fictional URLs are presented.

---

## 2. Run Locally: With Docker and Without

### Method A: With Docker (Recommended)

Prerequisites: [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

#### Start the Stack
```bash
make up
```
*Windows PowerShell equivalent:*
```powershell
docker compose up --build -d
```

This starts:
- **Backend API**: `http://localhost:8000` (FastAPI + LiteLLM + Uvicorn)
- **Frontend UI**: `http://localhost:3000` (React + Vite + Tailwind via Nginx)
- **Named Volume**: `lyftr_sqlite_data` mounted at `/data/app.db`

#### View Logs & Status
```bash
make status
make logs
```
*Windows PowerShell equivalent:*
```powershell
docker compose ps
docker compose logs -f
```

#### Run Automated Tests Inside Docker
```bash
make test
```
*Windows PowerShell equivalent:*
```powershell
docker compose exec -T backend pytest tests/ -v
```

#### Stop the Stack
```bash
make down
```
*Windows PowerShell equivalent:*
```powershell
docker compose down
```
*(Data in `/data/app.db` is safely preserved in the named Docker volume).*

---

### Method B: Without Docker (Local Development)

Prerequisites: Python 3.12+ and Node.js v20+.

#### 1. Backend Setup
```powershell
# Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Configure environment variables (copy example)
cp .env.example .env

# Run backend server (binds to port 8000)
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (in a separate terminal)
```powershell
cd frontend

# Install Node dependencies
npm install

# Start Vite development server (binds to port 3000)
npm run dev
```

#### 3. Run Backend Tests Locally
```powershell
.\.venv\Scripts\pytest backend/tests/ -v
```

---

## 3. Design Decisions

### A. Key Fallback & Resilience
- **Key Pool Architecture**: The application parses comma-separated keys from `LLM_API_KEYS` into ordered identifiers (`key_1`, `key_2`, ...). Real API keys are never exposed in JSON responses or log outputs.
- **Failover Triggering**: Whenever an attempt encounters an HTTP 429 (rate limit), quota exhaustion, or 5xx server error, the error is caught, `fallback_attempts` is incremented, and execution advances seamlessly to the next key in the pool.
- **Graceful Failure**: If all keys in the pool fail, the gateway returns a clean JSON HTTP 503 response (`{"detail": "all providers unavailable"}`) without leaking internal exception stack traces.

### B. Response Caching
- **LiteLLM Built-in Caching**: We utilize LiteLLM’s internal caching (`Cache(type="local")`, `enable_cache()`) keyed on the model name and the exact chronological sequence of messages (system prompt + history + current user message).
- **Cache-Hit Detection**: Rather than maintaining a separate caching dictionary, we inspect LiteLLM's internal response properties (`response._hidden_params.get("cache_hit") is True`).
- **Metadata Contract**:
  - Live Inference: reports `LIVE_INFERENCE`, the responding `key_id` (e.g. `key_1`), and `fallback_attempts`.
  - Cache Hit: reports `LLM_CACHE`, `key_id = null`, and `fallback_attempts = 0`, while preserving the original cached response text and token counts.
- **Cache & Failover Isolation**: When `X-Simulate-Failure` is supplied, the request explicitly passes `caching=False, cache={"no-store": True, "no-cache": True}` to LiteLLM so that simulated test requests actually test key failover instead of being bypassed by pre-existing cache hits, and simulated failures never corrupt the cache.

### C. SQLite Session Storage
- **Schema**: Auto-initialized on startup via SQLAlchemy declarative base:
  ```sql
  CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
  );
  ```
- **State Separation**: Only successful exchanges (user query and assistant response) are committed. Failed requests (HTTP 422, 503) are never written to the session history.
- **System Prompt Exclusion**: System prompts guide the LLM context but are never returned in `GET /sessions/{session_id}/messages`.
- **Persistent Volume**: In Docker, the database file resides at `/data/app.db` backed by the named volume `lyftr_sqlite_data`, surviving container stops, restarts, and image updates.

---

## 4. Verification: How to See Failover, Cache Hits and Token Usage

### 1. Verification via the Web UI (`http://localhost:3000`)
1. Open `http://localhost:3000` in your browser.
2. Send: `"What is the capital of France?"`
   - Observe the metadata badge below the reply: `LIVE_INFERENCE`, `gemini/gemini-flash-lite-latest`, `Key: key_1`.
3. Click **New Chat** (or open a new tab to start a new session), and send the exact same message: `"What is the capital of France?"`
   - Observe the green metadata badge: `LLM_CACHE`, `Key: (null)`, Latency under `5 ms`, identical token counts.
4. Click **Config** in the top navigation bar, select `key_1=429` under the **X-Simulate-Failure** dropdown, and send `"Explain gravity"`.
   - Observe the metadata: `LIVE_INFERENCE`, `Key: key_2`, and `(1 fallback)`.
5. Under Config, select `*=429` and send any message.
   - Observe the clean red error banner: `HTTP 503: All LLM providers are currently unavailable or rate-limited.`

### 2. Verification via cURL / PowerShell

#### Test 1: Live Inference
```powershell
$body = @{ session_id = "demo-1"; message = "Hello world" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body $body
```
*Expected metadata: `resolution_source: "LIVE_INFERENCE"`, `key_id: "key_1"`, `fallback_attempts: 0`.*

#### Test 2: Cache Hit
```powershell
$body = @{ session_id = "demo-2"; message = "Hello world" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body $body
```
*Expected metadata: `resolution_source: "LLM_CACHE"`, `key_id: null`, `fallback_attempts: 0`, identical reply.*

#### Test 3: Key Failover (key_1=429 &rarr; key_2 succeeds)
```powershell
$body = @{ session_id = "demo-3"; message = "Test failover" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Headers @{"X-Simulate-Failure"="key_1=429"} -Body $body
```
*Expected metadata: `resolution_source: "LIVE_INFERENCE"`, `key_id: "key_2"`, `fallback_attempts: 1`.*

#### Test 4: All Keys Failing (*=429 &rarr; HTTP 503)
```powershell
$body = @{ session_id = "demo-4"; message = "Fail all" } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Headers @{"X-Simulate-Failure"="*=429"} -Body $body
} catch {
  $_.Exception.Response
}
```
*Expected response: HTTP 503 `{"detail": "all providers unavailable"}`.*

#### Test 5: Verify Stored Session History
```powershell
Invoke-RestMethod -Uri http://localhost:8000/sessions/demo-1/messages
```
*Returns user and assistant messages with metadata; excludes system prompts.*

---

## 5. Setup Used: Editor and AI Tools

- **Primary Editor**: Cursor IDE on Windows 11
- **AI Agent & Assistant**: Antigravity / Gemini 3.8 Flash (High) in Autonomous Agent Mode
- **Terminal Shell**: Windows PowerShell 5.1 & PowerShell Core
- **Container Engine**: Docker Desktop v29.6.1 (WSL2 Linux integration)
- **Frameworks & Core Libraries**:
  - Backend: Python 3.12, FastAPI 0.165, LiteLLM 1.110, SQLAlchemy 2.1, Pydantic v2
  - Frontend: React 18, Vite 6, Tailwind CSS v3, Lucide Icons

---

## 6. Bonus Features Added

1. **Interactive Failure Simulation in UI**:
   - Added an on-demand dropdown in the frontend header allowing evaluators to trigger `key_1=429`, `key_1=500`, `key_1=429,key_2=500`, and `*=429` directly from the browser without needing cURL or Postman.
2. **Unified Dual-Mode Gateway**:
   - Supports seamless switching between mock mode (for deterministic automated CI testing) and live Google Gemini API mode via `MOCK_LLM=false` without rewriting code.
3. **Nginx Reverse-Proxy Integration**:
   - The production frontend Docker container includes reverse-proxy routes forwarding `/health`, `/chat`, and `/sessions/` directly to the backend container, eliminating CORS preflight overhead in containerized environments.
4. **Live Health & Key Pool Monitor**:
   - The header displays a real-time status pill indicating the number of configured keys and cache status dynamically fetched from `GET /health`.

---

## 7. Cloud Deployment Guide (Render & Vercel)

### Step 1: Deploy Backend to Render
1. Push this repository to GitHub.
2. Sign in to [Render](https://dashboard.render.com/) and click **New +** &rarr; **Blueprint**.
3. Select your GitHub repository. Render will automatically detect [`render.yaml`](file:///c:/Users/abhin/Downloads/lyftr_ai_chatbot/render.yaml).
4. In the configuration screen, supply your real Gemini keys under `LLM_API_KEYS` (format: `AIzaSyKey1...,AIzaSyKey2...`).
5. Click **Apply**. Render will:
   - Attach a 1GB persistent disk at `/data` for SQLite persistence.
   - Build and start FastAPI with Uvicorn.
6. Note your public backend URL (e.g. `https://lyftr-backend.onrender.com`).
7. Verify health: `curl https://lyftr-backend.onrender.com/health`.

### Step 2: Deploy Frontend to Vercel
1. Sign in to [Vercel](https://vercel.com/) and click **Add New** &rarr; **Project**.
2. Import this GitHub repository.
3. In Project Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add Environment Variable:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: Your Render backend URL (e.g. `https://lyftr-backend.onrender.com`)
5. Click **Deploy**.
6. Once deployed, add your Vercel URL (e.g. `https://your-app.vercel.app`) to `ALLOWED_ORIGINS` in your Render backend settings.
