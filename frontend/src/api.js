const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function pdfUrl(documentId) {
  return `${BASE_URL}/pdf/${documentId}`;
}

export async function uploadDocument(files) {
  const formData = new FormData();
  const fileList = Array.isArray(files) ? files : [files];
  fileList.forEach(f => formData.append('files', f));
  const res = await fetch(`${BASE_URL}/upload`, { method: 'POST', body: formData });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function getDocuments() {
  const res = await fetch(`${BASE_URL}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${BASE_URL}/documents/${documentId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete document');
  return res.json();
}

export async function streamChat(question, documentId, history, onToken, onDone, onError) {
  let res;
  try {
    res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId, question, history }),
    });
  } catch {
    onError(new Error('Network error'));
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Something went wrong' }));
    onError(new Error(err.detail || 'Chat request failed'));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;
        const data = JSON.parse(raw);
        if (data.done) {
          onDone(data.sources || []);
          return;
        }
        if (data.token !== undefined) onToken(data.token);
      }
    }
  } catch (e) {
    onError(new Error('Stream interrupted: ' + e.message));
  }
}
