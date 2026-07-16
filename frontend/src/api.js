const BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8031';

let token = localStorage.getItem('multi-agent-token') || '';

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${BASE}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

export const api = {
  async login(customerKey = 'ana') {
    const data = await request('/api/auth/token', { method: 'POST', body: JSON.stringify({ customer_key: customerKey }) });
    token = data.access_token;
    localStorage.setItem('multi-agent-token', token);
    return data.customer;
  },
  health: () => request('/api/health'),
  agents: () => request('/api/agents'),
  metrics: () => request('/api/metrics'),
  handoffs: (id) => request(`/api/handoffs?conversation_id=${encodeURIComponent(id)}`),
  memory: (key) => request(`/api/memory/${encodeURIComponent(key)}`),
  latestConversation: () => request('/api/conversations/latest'),
  guardrails: (view = 'events') => request(`/api/guardrails/${view}`),
  chat: (message, conversationId) => request('/api/chat', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId || null }) }),
  updateAgent: (key, update) => request(`/api/admin/agents/${key}`, { method: 'PATCH', headers: { 'X-Admin-Key': import.meta.env.VITE_ADMIN_KEY || '' }, body: JSON.stringify(update) }),
  evalRuns: () => request('/api/eval/runs', { headers: { 'X-Admin-Key': import.meta.env.VITE_ADMIN_KEY || '' } }),
  async streamEvents(onEvent, signal) {
    const response = await fetch(`${BASE}/api/events/stream`, { headers: { Authorization: `Bearer ${token}` }, signal });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop();
      for (const chunk of chunks) {
        if (chunk.startsWith('data: ')) {
          try { onEvent(JSON.parse(chunk.slice(6))); } catch { /* linha incompleta, ignora */ }
        }
      }
    }
  },
};
