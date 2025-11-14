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
  clip_count?: number;
  description?: string | null;
  hashtags?: string[];
  metadata_json?: {
    platform?: string;
    like_count?: number;
    comment_count?: number;
    view_count?: number;
    upload_date?: string;
    thumbnail?: string;
    [key: string]: any;
  };
  media_path?: string | null;
  created_at?: string;
  score?: number;
  snippet?: string;
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

// =============================================================================
// URL-first flow (new endpoints for Page 1)
// =============================================================================
// frontend/src/api.ts
export async function ingestUrl(link: string) {
  const r = await fetch(`/api/videos/ingest_url`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ link })
  });
  if (!r.ok) throw new Error(`ingest_url failed: ${r.status}`);
  return r.json() as Promise<{ 
    video_id: string; 
    clip_count?: number; 
    description?: string;
    title?: string;
    author?: string;
    hashtags?: string[];
    already_exists?: boolean;
  }>;
}

// Video meta (caption + clip_count)
export async function getVideoMeta(videoId: string) {
  const res = await fetch(`/api/videos/${videoId}/meta`);
  if (!res.ok) throw new Error(`meta failed: ${res.status}`);
  return res.json() as Promise<{ clip_count: number; description?: string }>;
}

export async function getStreamUrl(videoId: string, clip?: number) {
  const res = await fetch(`/api/videos/${videoId}/stream${clip ? `?clip=${clip}` : ''}`);
  if (!res.ok) throw new Error(`stream failed: ${res.status}`);
  return res.json() as Promise<{ url: string }>;
}


// Generate transcript for a specific clip
export async function generateTranscript(videoId: string, clip?: number) {
  const res = await fetch(`/api/videos/${videoId}:generate_transcript${clip ? `?clip=${clip}` : ''}`, { method: 'POST' });
  if (!res.ok) {
    const txt = await res.text().catch(()=> '');
    throw new Error(`generate_transcript failed: ${res.status} ${txt}`);
  }
  return res.json() as Promise<{ video_id: string; text: string; title?: string; url: string; media_path?: string }>;
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

export async function deleteVideo(videoId: VideoId) {
  return jsonFetch(`${API_BASE}/videos/${videoId}`, {
    method: 'DELETE',
  });
}

// =============================================================================
// Search and RAG endpoints
// =============================================================================

export interface SearchHit {
  video_id: string;
  title: string | null;
  author: string | null;
  url: string;
  score: number;
  snippet: string;
  media_path: string | null;
  source: string | null;
  description: string | null;
}

export interface SearchResponse {
  query: string;
  hits: SearchHit[];
  total: number;
}

export interface RAGSource {
  video_id: string;
  title: string | null;
  author: string | null;
  url: string;
  snippet: string;
  score: number;
}

export interface RAGResponse {
  query: string;
  answer: string;
  sources: RAGSource[];
}

export async function searchVideos(query: string, k: number = 10, k_ann?: number) {
  return jsonFetch<SearchResponse>(`${API_BASE}/search/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k, k_ann }),
  });
}

export async function ragAnswer(query: string, k_ann: number = 20, k_final: number = 5) {
  return jsonFetch<RAGResponse>(`${API_BASE}/search/rag`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k_ann, k_final }),
  });
}

// =============================================================================
// Collections endpoints
// =============================================================================

export interface Collection {
  id: string;
  query: string;
  ai_answer: string | null;
  video_ids: string[];
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface CollectionWithVideos extends Collection {
  videos: VideoSummary[];
}

export async function saveCollection(
  query: string,
  aiAnswer: string | null,
  videoIds: string[],
  metadata?: Record<string, any>
) {
  return jsonFetch<Collection>(`${API_BASE}/collections/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      ai_answer: aiAnswer,
      video_ids: videoIds,
      metadata_json: metadata || {},
    }),
  });
}

export async function getCollections() {
  return jsonFetch<Collection[]>(`${API_BASE}/collections/`);
}

export async function getCollection(collectionId: string) {
  return jsonFetch<CollectionWithVideos>(`${API_BASE}/collections/${collectionId}`);
}

export async function deleteCollection(collectionId: string) {
  return jsonFetch<{ message: string; collection_id: string }>(`${API_BASE}/collections/${collectionId}`, {
    method: 'DELETE',
  });
}

// =============================================================================
// Retrieval Feedback endpoints
// =============================================================================

export interface SimilarQuery {
  query: string;
  similarity: number;
  good_video_ids: string[];
  bad_video_ids: string[];
}

export interface SimilarQueriesResponse {
  query: string;
  similar_queries: SimilarQuery[];
}

export async function saveRetrievalFeedback(query: string, videoId: string, feedback: 'good' | 'bad') {
  return jsonFetch<{ status: string; message: string }>(`${API_BASE}/search/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      video_id: videoId,
      feedback,
    }),
  });
}

export interface VideoFeedback {
  video_id: string;
  feedback: 'good' | 'bad';
}

export interface GetFeedbackResponse {
  query: string;
  feedback: VideoFeedback[];
}

export async function getRetrievalFeedback(query: string, videoIds: string[]) {
  return jsonFetch<GetFeedbackResponse>(`${API_BASE}/search/feedback/get`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      video_ids: videoIds,
    }),
  });
}

export async function findSimilarQueries(query: string, k: number = 10, k_ann: number = 50) {
  return jsonFetch<SimilarQueriesResponse>(`${API_BASE}/search/similar-queries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, k, k_ann }),
  });
}
