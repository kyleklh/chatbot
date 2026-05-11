const STORAGE_KEY = 'docurag.conversations.v1';
const ACTIVE_KEY = 'docurag.activeConversationId.v1';

export function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveConversations(conversations) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch {
    /* quota or disabled */
  }
}

export function loadActiveConversationId() {
  try {
    return localStorage.getItem(ACTIVE_KEY) || null;
  } catch {
    return null;
  }
}

export function saveActiveConversationId(id) {
  try {
    if (id) localStorage.setItem(ACTIVE_KEY, id);
    else localStorage.removeItem(ACTIVE_KEY);
  } catch {
    /* ignore */
  }
}

export function newConversation() {
  return {
    id: crypto.randomUUID(),
    title: 'New chat',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

export function autoTitle(text) {
  if (!text) return 'New chat';
  const trimmed = text.trim().replace(/\s+/g, ' ');
  return trimmed.length > 40 ? trimmed.slice(0, 40) + '…' : trimmed;
}

export function groupByDate(conversations) {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;
  const startOfLast7 = startOfToday - 7 * 24 * 60 * 60 * 1000;

  const groups = { Today: [], Yesterday: [], 'Last 7 days': [], Older: [] };
  const sorted = [...conversations].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  for (const c of sorted) {
    const ts = c.updatedAt || c.createdAt || 0;
    if (ts >= startOfToday) groups.Today.push(c);
    else if (ts >= startOfYesterday) groups.Yesterday.push(c);
    else if (ts >= startOfLast7) groups['Last 7 days'].push(c);
    else groups.Older.push(c);
  }
  return groups;
}
