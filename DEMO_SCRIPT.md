# 2–3 Minute Demo Video Script

This script guides your screen recording for the Lyftr AI assignment submission.

---

## Preparation Checklist
- Have the Web UI open in your browser (`http://localhost:3000` or deployed Vercel URL).
- Have a terminal open for showing `GET /health` or curl commands if desired.
- Open DevTools (Network tab) if you want to visually highlight headers and response payloads.

---

## Timestamp Breakdown (Total: 2m 30s)

### 0:00 – 0:30 | Introduction & Architecture
**Visual**: Show the Web UI homepage with clean dark mode SaaS styling.
**Spoken Script**:
> *"Hi everyone, welcome to the demo of my Lyftr AI LLM Gateway and Chatbot. This is a full-stack resilient AI application built with a React and Tailwind frontend, a FastAPI backend with LiteLLM integration, and a persistent SQLite database. The gateway features automatic key failover across multiple Gemini API keys, built-in response caching, and a test simulation hook."*

---

### 0:30 – 1:00 | Multi-Turn Chat & Live Inference
**Visual**: Type and send a question, e.g., `"What is the capital of France?"`.
**Spoken Script**:
> *"Let's start by sending a message in a new session. Notice the response comes back instantly. Next to the AI reply, we can see the full required metadata:
> - Resolution source: `LIVE_INFERENCE`
> - Model: `gemini/gemini-flash-lite-latest`
> - Latency: server-measured response time in milliseconds
> - Per-request token usage: showing prompt tokens and completion tokens
> - And the responding key alias: `key_1` with 0 fallback attempts."*

---

### 1:00 – 1:30 | Response Caching Demonstration
**Visual**: Click **New Chat** to start a new session (new `session_id`). Send the exact same question: `"What is the capital of France?"`.
**Spoken Script**:
> *"Now, let's start a brand new session with a new session ID and send the exact same query. Watch what happens:
> Notice the green badge: resolution source is now `LLM_CACHE`. The reply text is completely identical, the latency dropped significantly to near-instantaneous speed, the key ID is correctly null, and the original cached token count is preserved. LiteLLM's internal caching correctly identified the identical message context across sessions."*

---

### 1:30 – 2:05 | Automatic Key Failover (`X-Simulate-Failure: key_1=429`)
**Visual**: Click the **Config** drawer in the header. Select `key_1=429` in the dropdown. Send a new query, e.g., `"Explain quantum computing in one sentence"`.
**Spoken Script**:
> *"Next, let's demonstrate automatic key failover using the assignment's test hook. I'll open Config and simulate HTTP 429 rate limit on `key_1`. Now when I send this message, watch the metadata:
> The request succeeds seamlessly for the user! In the metadata, we see `key_2` answered the request, and `fallback_attempts` is accurately reported as 1. The user never saw an error screen or stack trace."*

---

### 2:05 – 2:20 | Exhaustion / 503 Handling (`*=429`)
**Visual**: Change the dropdown to `*=429` and send a message.
**Spoken Script**:
> *"What happens if all provider keys fail? Let's simulate `*=429`. When sent, the application catches the exhaustion and returns a clean HTTP 503 error banner stating that all providers are unavailable. Crucially, nothing failed is written to our SQLite session history."*

---

### 2:20 – 2:30 | SQLite Session History & Conclusion
**Visual**: Refresh or navigate to `/sessions/{session_id}/messages` or show the terminal with persisted history.
**Spoken Script**:
> *"All conversation history is strictly preserved in SQLite per session, surviving container restarts via Docker volumes. The entire stack starts with a single `make up` command and passes all 28 automated tests. Thank you for watching!"*
