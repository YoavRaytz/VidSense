// frontend/src/api.ts
// Base URL for the backend API.
// In dev, prefer a Vite proxy: set VITE_API="/api" in .env.local (or default here).
export const API_BASE = import.meta.env.VITE_API ?? '/api';

// ---- Small helper ----
async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---- Types you may use in components ----
export type VideoId = string;

export interface VideoSummary {
  id: VideoId;
  source: string;
  url: string;
  title?: string | null;
  author?: string | null;
  duration_sec?: number | null;
  media_path?: string | null;
  created_at?: string;
}

export interface TranscriptDTO {
  video_id: VideoId;
  title?: string | null;
  url: string;
  media_path?: string | null;
  text: string;
}

// =============================================================================
// Legacy endpoints (kept for backward compatibility with existing pages)
// =============================================================================
export async function search(query: string, k = 10) {
  return jsonFetch<{ hits: any[] }>(`${API_BASE}/search/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k }),
  });
}

export async function ingestFolder(base_dir: string, source = 'instagram') {
  return jsonFetch(`${API_BASE}/ingest/folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_dir, source }),
  });
}

// Lists saved videos (named *listTranscripts* historically in your app)
export async function listTranscripts() {
  return jsonFetch<VideoSummary[]>(`${API_BASE}/videos/`);
}

// Get a video (legacy endpoint that returns video + transcript combined)
export async function getVideo(video_id: VideoId) {
  return jsonFetch(`${API_BASE}/videos/${video_id}`);
}

// Update transcript via legacy endpoint (PUT /videos/{id})
export async function updateVideoTranscript(video_id: VideoId, text: string) {
  return jsonFetch(`${API_BASE}/videos/${video_id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

// RAG answer (legacy)
export async function ragAnswer(query: string, k_ann = 50, k_final = 10) {
  return jsonFetch(`${API_BASE}/rag/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k_ann, k_final }),
  });
}

// =============================================================================
// URL-first flow (new endpoints for Page 1)
// =============================================================================
export async function ingestUrl(link: string) {
  return jsonFetch<{ video_id: VideoId }>(`${API_BASE}/videos/ingest_url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ link }),
  });
}

export async function getStreamUrl(videoId: VideoId) {
  return jsonFetch<{ url: string }>(`${API_BASE}/videos/${videoId}/stream`);
}

export async function generateTranscript(videoId: VideoId) {
  return jsonFetch<TranscriptDTO>(`${API_BASE}/videos/${videoId}:generate_transcript`, {
    method: 'POST',
  });
}

// NEW transcript CRUD (separate from legacy PUT /videos/{id})
export async function getTranscript(videoId: VideoId) {
  return jsonFetch<TranscriptDTO>(`${API_BASE}/videos/${videoId}/transcript`);
}

export async function putTranscript(videoId: VideoId, text: string) {
  return jsonFetch(`${API_BASE}/videos/${videoId}/transcript`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}
