const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function pdfUrl(documentId) {
  return `${BASE_URL}/pdf/${documentId}`;
}

export function uploadDocument(files, { onProgress, onUploadComplete } = {}) {
  const formData = new FormData();
  const fileList = Array.isArray(files) ? files : [files];
  fileList.forEach(f => formData.append('files', f));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE_URL}/upload`);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress(Math.min(99, Math.round((e.loaded / e.total) * 100)));
        }
      };
    }
    if (xhr.upload && onUploadComplete) {
      xhr.upload.onload = () => onUploadComplete();
    }

    xhr.onerror = () => reject(new Error('Network error'));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error('Invalid response from server'));
        }
      } else {
        let detail = 'Upload failed';
        try { detail = JSON.parse(xhr.responseText).detail || detail; } catch { /* keep default */ }
        reject(new Error(detail));
      }
    };

    xhr.send(formData);
  });
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

export async function streamChat(question, documentId, history, onToken, onDone, onError, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_id: documentId,
        document_ids: options.documentIds || null,
        question,
        history,
      }),
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
