import { useState, useEffect } from 'react';
import { listTranscripts, getStreamUrl, getTranscript, getVideoMeta, deleteVideo, putTranscript } from '../api';
import type { VideoSummary } from '../api';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptViewer from '../components/TranscriptViewer';

interface VideoDetail extends VideoSummary {
  description?: string | null;
  clip_count: number;
}

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState<VideoDetail | null>(null);
  
  // Selected video state
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [clip, setClip] = useState(1);
  
  // Selection and delete state
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [hoveredVideoId, setHoveredVideoId] = useState<string | null>(null);
  
  // Edit state
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    loadVideos();
  }, []);

  async function loadVideos() {
    try {
      setLoading(true);
      const data = await listTranscripts();
      // Fetch additional metadata for each video
      const enrichedVideos = await Promise.all(
        data.map(async (v) => {
          try {
            const meta = await getVideoMeta(v.id);
            return { ...v, clip_count: meta.clip_count || 1, description: meta.description };
          } catch {
            return { ...v, clip_count: 1, description: undefined };
          }
        })
      );
      setVideos(enrichedVideos);
    } catch (e) {
      console.error('Failed to load videos:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleVideoClick(video: VideoDetail) {
    setSelectedVideo(video);
    setClip(1);
    
    try {
      // Load stream URL
      const stream = await getStreamUrl(video.id, 1);
      setStreamUrl(stream.url);
      
      // Load transcript
      const t = await getTranscript(video.id);
      setTranscript(t.text || '');
    } catch (e) {
      console.error('Failed to load video details:', e);
    }
  }

  async function handleClipChange(newClip: number) {
    if (!selectedVideo) return;
    setClip(newClip);
    
    try {
      const stream = await getStreamUrl(selectedVideo.id, newClip);
      setStreamUrl(stream.url);
    } catch (e) {
      console.error('Failed to load clip:', e);
    }
  }

  function handleBack() {
    setSelectedVideo(null);
    setStreamUrl(null);
    setTranscript('');
    setClip(1);
    setStatusMsg(null);
  }

  async function handleSaveTranscript() {
    if (!selectedVideo) return;
    
    setSaving(true);
    setStatusMsg(null);
    
    try {
      await putTranscript(selectedVideo.id, transcript);
      setStatusMsg('✅ Transcript saved successfully!');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e) {
      console.error('Failed to save transcript:', e);
      setStatusMsg('❌ Failed to save transcript. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(videoId: string, event?: React.MouseEvent) {
    // Prevent clicking the card
    event?.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this video? This cannot be undone.')) {
      return;
    }

    try {
      await deleteVideo(videoId);
      // Refresh the list
      await loadVideos();
      // If we're viewing the deleted video, go back to list
      if (selectedVideo?.id === videoId) {
        handleBack();
      }
    } catch (e) {
      console.error('Failed to delete video:', e);
      alert('Failed to delete video. Please try again.');
    }
  }

  function toggleSelection(videoId: string, event: React.ChangeEvent<HTMLInputElement> | React.MouseEvent) {
    event.stopPropagation();
    const newSelected = new Set(selectedIds);
    if (newSelected.has(videoId)) {
      newSelected.delete(videoId);
    } else {
      newSelected.add(videoId);
    }
    setSelectedIds(newSelected);
  }

  function selectAll() {
    setSelectedIds(new Set(videos.map(v => v.id)));
  }

  function deselectAll() {
    setSelectedIds(new Set());
  }

  async function deleteSelected() {
    if (selectedIds.size === 0) {
      alert('No videos selected');
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedIds.size} video(s)? This cannot be undone.`)) {
      return;
    }

    try {
      // Delete all selected videos
      await Promise.all(Array.from(selectedIds).map(id => deleteVideo(id)));
      // Clear selection and refresh
      setSelectedIds(new Set());
      setSelectionMode(false);
      await loadVideos();
      // If viewing a deleted video, go back
      if (selectedVideo && selectedIds.has(selectedVideo.id)) {
        handleBack();
      }
    } catch (e) {
      console.error('Failed to delete videos:', e);
      alert('Failed to delete some videos. Please try again.');
    }
  }

  function formatDate(dateStr?: string | null) {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return '';
    }
  }

  function formatDuration(sec?: number | null) {
    if (!sec) return '';
    const mins = Math.floor(sec / 60);
    const secs = sec % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  // Detail view
  if (selectedVideo) {
    return (
      <div className="grid-2">
        {/* Left: video player */}
        <div className="card">
          <div className="row" style={{ marginBottom: 12, alignItems: 'center', justifyContent: 'space-between' }}>
            <button className="btn" onClick={handleBack}>← Back to List</button>
          </div>
          
          <h3 className="section-title">{selectedVideo.title || 'Video'}</h3>
          {selectedVideo.author && (
            <p className="muted" style={{ margin: '0 0 12px 0' }}>by {selectedVideo.author}</p>
          )}
          
          {selectedVideo.clip_count > 1 && (
            <div className="alert" style={{ marginBottom: 10 }}>
              📚 This post has <b>{selectedVideo.clip_count}</b> videos.
            </div>
          )}
          
          <VideoPlayer
            videoId={selectedVideo.id}
            streamUrl={streamUrl}
            clipCount={selectedVideo.clip_count}
            clip={clip}
            onClipChange={handleClipChange}
          />
        </div>

        {/* Right: transcript */}
        <TranscriptViewer
          transcript={transcript}
          description={selectedVideo.description || undefined}
          onTranscriptChange={setTranscript}
          onSave={handleSaveTranscript}
          saving={saving}
          statusMsg={statusMsg}
          readOnly={false}
        />
      </div>
    );
  }

  // List view
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3 className="section-title" style={{ margin: 0 }}>Saved Videos</h3>
        
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {selectionMode && (
            <>
              <span className="muted" style={{ fontSize: 13 }}>
                {selectedIds.size} selected
              </span>
              <button
                className="btn"
                onClick={selectAll}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
              >
                Select All
              </button>
              <button
                className="btn"
                onClick={deselectAll}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
              >
                Deselect All
              </button>
              <button
                onClick={deleteSelected}
                disabled={selectedIds.size === 0}
                style={{
                  padding: '6px 16px',
                  backgroundColor: selectedIds.size > 0 ? '#dc3545' : '#666',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: selectedIds.size > 0 ? 'pointer' : 'not-allowed',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                }}
              >
                Delete Selected
              </button>
            </>
          )}
          <button
            className="btn"
            onClick={() => {
              setSelectionMode(!selectionMode);
              setSelectedIds(new Set());
            }}
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            {selectionMode ? 'Cancel' : 'Select'}
          </button>
        </div>
      </div>
      
      {loading ? (
        <p className="muted">Loading videos...</p>
      ) : videos.length === 0 ? (
        <p className="muted">No videos saved yet. Go to the Ingest page to add some!</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {videos.map(video => (
            <div
              key={video.id}
              onClick={() => !selectionMode && handleVideoClick(video)}
              style={{
                padding: 16,
                background: '#0b1220',
                border: '1px solid #1f2937',
                borderRadius: 8,
                cursor: selectionMode ? 'default' : 'pointer',
                transition: 'border-color 0.15s ease, background 0.15s ease',
                position: 'relative',
              }}
              onMouseEnter={e => {
                setHoveredVideoId(video.id);
                if (!selectionMode) {
                  e.currentTarget.style.borderColor = '#3b82f6';
                  e.currentTarget.style.background = '#0f1420';
                }
              }}
              onMouseLeave={e => {
                setHoveredVideoId(null);
                e.currentTarget.style.borderColor = '#1f2937';
                e.currentTarget.style.background = '#0b1220';
              }}
            >
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div style={{ flex: 1, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  {selectionMode && (
                    <input
                      type="checkbox"
                      checked={selectedIds.has(video.id)}
                      onChange={(e) => toggleSelection(video.id, e)}
                      onClick={(e) => e.stopPropagation()}
                      style={{
                        width: 18,
                        height: 18,
                        cursor: 'pointer',
                        marginTop: 2,
                      }}
                    />
                  )}
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: '0 0 4px 0', fontSize: 16, fontWeight: 600 }}>
                      {video.title || 'Untitled Video'}
                    </h4>
                    {video.author && (
                      <p className="muted" style={{ margin: '0 0 4px 0', fontSize: 13 }}>
                        by {video.author}
                      </p>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', position: 'relative' }}>
                  {video.duration_sec && (
                    <span className="muted" style={{ fontSize: 13 }}>
                      ⏱️ {formatDuration(video.duration_sec)}
                    </span>
                  )}
                  {video.clip_count > 1 && (
                    <span className="muted" style={{ fontSize: 13 }}>
                      📚 {video.clip_count} clips
                    </span>
                  )}
                  {!selectionMode && hoveredVideoId === video.id && (
                    <button
                      onClick={(e) => handleDelete(video.id, e)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#dc3545',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        transition: 'background-color 0.2s',
                        fontWeight: 500,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#c82333')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#dc3545')}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
              
              <div className="row" style={{ gap: 12, flexWrap: 'wrap' }}>
                <span style={{ 
                  fontSize: 11, 
                  padding: '2px 8px', 
                  background: '#1f2937', 
                  borderRadius: 4,
                  textTransform: 'uppercase',
                  letterSpacing: 0.5
                }}>
                  {video.source}
                </span>
                {video.created_at && (
                  <span className="muted" style={{ fontSize: 12 }}>
                    {formatDate(video.created_at)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
