/**
 * API Service for interacting with the Lyftr AI backend.
 */

const envUrl = import.meta.env.VITE_API_BASE_URL;

// Robust URL resolution:
// 1. If explicit env variable is set (e.g. in cloud Vercel/Render deployment), use it.
// 2. If running locally on port 3000 (served by Nginx container), use relative '' so Nginx proxies.
// 3. Fallback to direct backend URL for standalone dev servers.
const getBaseUrl = () => {
  if (envUrl !== undefined && envUrl !== '') {
    return envUrl;
  }
  if (typeof window !== 'undefined' && window.location.port === '3000') {
    return '';
  }
  return 'http://localhost:8000';
};

const BASE_URL = getBaseUrl();

/**
 * Fetch health status of backend, database, and key pool.
 */
export async function getHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error('Failed to fetch health status:', err);
    return { status: 'error', keys_configured: 0, cache_enabled: false };
  }
}

/**
 * Send a chat message.
 * @param {Object} params
 * @param {string} params.sessionId
 * @param {string} params.message
 * @param {string} [params.systemPrompt]
 * @param {string} [params.simulateFailure]
 */
export async function postChat({ sessionId, message, systemPrompt, simulateFailure }) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (simulateFailure) {
    headers['X-Simulate-Failure'] = simulateFailure;
  }

  const payload = {
    session_id: sessionId,
    message: message.trim(),
  };

  if (systemPrompt && systemPrompt.trim()) {
    payload.system_prompt = systemPrompt.trim();
  }

  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  const data = await res.json().catch(() => ({ detail: 'Invalid response from server' }));

  if (!res.ok) {
    const errorMsg = data.detail || `Server returned error ${res.status}`;
    const err = new Error(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

/**
 * Retrieve chronological conversation history for a session.
 * @param {string} sessionId
 */
export async function getSessionMessages(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${encodeURIComponent(sessionId)}/messages`);
  const data = await res.json().catch(() => ({ detail: 'Failed to parse session history' }));

  if (!res.ok) {
    const err = new Error(data.detail || `Error fetching session history: ${res.status}`);
    err.status = res.status;
    throw err;
  }

  return data;
}
