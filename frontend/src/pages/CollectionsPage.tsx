import { useEffect, useState } from 'react';
import { getCollections, deleteCollection, getCollection, Collection, CollectionWithVideos, getStreamUrl, getTranscript, listTranscripts, type VideoSummary } from '../api';
import ReactMarkdown from 'react-markdown';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptViewer from '../components/TranscriptViewer';
import VideoMetadata from '../components/VideoMetadata';

interface VideoDetail extends VideoSummary {
  clip_count: number;
}

export default function CollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedCollection, setExpandedCollection] = useState<CollectionWithVideos | null>(null);
  const [loadingExpanded, setLoadingExpanded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Video detail view state (same as SearchPage)
  const [selectedVideo, setSelectedVideo] = useState<VideoDetail | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [clip, setClip] = useState(1);
  const [showMetadata, setShowMetadata] = useState(true);

  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    try {
      setLoading(true);
      const data = await getCollections();
      setCollections(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this collection?')) return;
    
    try {
      await deleteCollection(id);
      setCollections(collections.filter(c => c.id !== id));
      if (expandedId === id) {
        setExpandedId(null);
        setExpandedCollection(null);
      }
    } catch (err: any) {
      alert('Failed to delete: ' + err.message);
    }
  };

  const handleToggleExpand = async (collectionId: string) => {
    if (expandedId === collectionId) {
      // Collapse
      setExpandedId(null);
      setExpandedCollection(null);
    } else {
      // Expand - fetch full details
      setExpandedId(collectionId);
      setLoadingExpanded(true);
      try {
        const fullCollection = await getCollection(collectionId);
        setExpandedCollection(fullCollection);
      } catch (err: any) {
        alert('Failed to load collection details: ' + err.message);
        setExpandedId(null);
      } finally {
        setLoadingExpanded(false);
      }
    }
  };

  const handleVideoClick = async (video: VideoSummary) => {
    try {
      // Get full video metadata from list endpoint
      const videos = await listTranscripts();
      const fullVideo = videos.find(v => v.id === video.id);
      
      const videoDetail: VideoDetail = fullVideo ? {
        ...video,
        ...fullVideo,
        clip_count: fullVideo.clip_count || 1,
      } : {
        ...video,
        clip_count: video.clip_count || 1,
      };
      
      setSelectedVideo(videoDetail);
      setClip(1);
      
      // Load stream URL for first clip
      const stream = await getStreamUrl(video.id, 1);
      setStreamUrl(stream.url);
      
      // Load transcript
      const t = await getTranscript(video.id);
      setTranscript(t.text || '');
    } catch (e) {
      console.error('Failed to load video:', e);
      alert(`Failed to load video: ${e}`);
    }
  };

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

  function handleCloseVideo() {
    setSelectedVideo(null);
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 32, textAlign: 'center' }}>
        <p>Loading collections...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <p style={{ color: '#ef4444' }}>Error: {error}</p>
      </div>
    );
  }

  // Show video detail view if a video is selected
  if (selectedVideo) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Back button */}
        <div className="card">
          <button className="btn" onClick={handleCloseVideo}>
            ← Back to Collections
          </button>
        </div>

        {/* Video detail in grid layout */}
        <div className="grid-2">
          {/* Left: video player */}
          <div className="card">
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

          {/* Right: metadata + transcript */}
          <div className="card">
            <VideoMetadata 
              video={selectedVideo as any}
              showToggle={true}
              onToggleVisibility={setShowMetadata}
              initiallyVisible={showMetadata}
            />
            
            <TranscriptViewer
              transcript={transcript}
              description={selectedVideo.description || undefined}
              readOnly={true}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, marginBottom: 8 }}>
          📚 Collections
        </h1>
        <p className="muted">
          Your saved search results and AI answers
        </p>
      </div>

      {collections.length === 0 ? (
        <div style={{
          padding: 48,
          textAlign: 'center',
          background: '#0b1220',
          border: '1px solid #1f2937',
          borderRadius: 12,
        }}>
          <p style={{ fontSize: 18, marginBottom: 8 }}>No collections yet</p>
          <p className="muted">
            Save search results from the Search page to see them here
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {collections.map((collection) => {
            const isExpanded = expandedId === collection.id;
            const fullData = isExpanded ? expandedCollection : null;

            return (
              <div
                key={collection.id}
                style={{
                  background: '#0b1220',
                  border: '1px solid #1f2937',
                  borderRadius: 12,
                  padding: 24,
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#3b82f6';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#1f2937';
                }}
              >
                {/* Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 16,
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 8,
                    }}>
                      <span style={{ fontSize: 20 }}>🔍</span>
                      <h3 style={{
                        fontSize: 18,
                        fontWeight: 600,
                        margin: 0,
                      }}>
                        {collection.query}
                      </h3>
                    </div>
                    <p className="muted" style={{ fontSize: 13, margin: 0 }}>
                      {formatDate(collection.created_at)}
                      {' • '}
                      {collection.video_ids?.length || 0} video(s)
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => handleToggleExpand(collection.id)}
                      style={{
                        padding: '6px 12px',
                        background: '#2563eb',
                        border: 'none',
                        borderRadius: 6,
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: 500,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#1d4ed8';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#2563eb';
                      }}
                    >
                      {isExpanded ? '▲ Collapse' : '▼ View Sources'}
                    </button>
                    
                    <button
                      onClick={() => handleDelete(collection.id)}
                      style={{
                        padding: '6px 12px',
                        background: '#dc2626',
                        border: 'none',
                        borderRadius: 6,
                        color: 'white',
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: 500,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#b91c1c';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#dc2626';
                      }}
                    >
                      🗑️ Delete
                    </button>
                  </div>
                </div>

                {/* AI Answer */}
                {collection.ai_answer && (
                  <div style={{
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: 8,
                    padding: 16,
                    marginBottom: 16,
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 12,
                    }}>
                      <span style={{ fontSize: 16 }}>🤖</span>
                      <h4 style={{
                        fontSize: 14,
                        fontWeight: 600,
                        margin: 0,
                        color: '#60a5fa',
                      }}>
                        AI Answer
                      </h4>
                    </div>
                    <div style={{
                      fontSize: 14,
                      lineHeight: 1.6,
                    }}>
                      <ReactMarkdown>{collection.ai_answer}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Expanded Sources */}
                {isExpanded && (
                  <div style={{
                    marginTop: 16,
                    paddingTop: 16,
                    borderTop: '1px solid #1f2937',
                  }}>
                    {loadingExpanded ? (
                      <p className="muted" style={{ textAlign: 'center', padding: 16 }}>
                        Loading sources...
                      </p>
                    ) : fullData?.videos && fullData.videos.length > 0 ? (
                      <>
                        <h4 style={{
                          fontSize: 16,
                          fontWeight: 600,
                          marginBottom: 16,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                        }}>
                          <span>📚</span>
                          <span>Sources ({fullData.videos.length})</span>
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          {fullData.videos.map((video, idx) => (
                            <div
                              key={video.id}
                              onClick={() => handleVideoClick(video)}
                              style={{
                                padding: 16,
                                background: '#1e293b',
                                border: '1px solid #334155',
                                borderRadius: 8,
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#3b82f6';
                                e.currentTarget.style.background = '#1f2937';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#334155';
                                e.currentTarget.style.background = '#1e293b';
                              }}
                            >
                              <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start',
                                marginBottom: 8,
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                                  <span style={{
                                    background: '#2563eb',
                                    color: 'white',
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    fontSize: 12,
                                    fontWeight: 600,
                                  }}>
                                    [{idx + 1}]
                                  </span>
                                  <h4 style={{ margin: 0, fontSize: 16 }}>
                                    {video.title || 'Untitled Video'}
                                  </h4>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                  {video.score !== undefined && (
                                    <span style={{
                                      color: '#10b981',
                                      fontSize: 13,
                                      fontWeight: 600,
                                    }}>
                                      {(video.score * 100).toFixed(1)}% match
                                    </span>
                                  )}
                                  {video.clip_count && (
                                    <span className="muted" style={{ fontSize: 13 }}>
                                      {video.clip_count} clip{video.clip_count !== 1 ? 's' : ''}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {video.author && (
                                <p className="muted" style={{ margin: '4px 0 8px 0', fontSize: 13 }}>
                                  by {video.author}
                                </p>
                              )}

                              {/* Show snippet if available, otherwise description */}
                              {video.snippet ? (
                                <p style={{
                                  fontSize: 14,
                                  lineHeight: 1.6,
                                  color: '#d1d5db',
                                  margin: '8px 0 0 0',
                                }}>
                                  {video.snippet}
                                </p>
                              ) : video.description && (
                                <p style={{
                                  fontSize: 14,
                                  lineHeight: 1.6,
                                  color: '#d1d5db',
                                  margin: '8px 0 0 0',
                                }}>
                                  {video.description.length > 200
                                    ? video.description.slice(0, 200) + '...'
                                    : video.description}
                                </p>
                              )}

                              {video.hashtags && video.hashtags.length > 0 && (
                                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                  {video.hashtags.map((tag: string) => (
                                    <span
                                      key={tag}
                                      style={{
                                        background: '#334155',
                                        color: '#60a5fa',
                                        padding: '2px 8px',
                                        borderRadius: 4,
                                        fontSize: 12,
                                      }}
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="muted" style={{ textAlign: 'center', padding: 16 }}>
                        No videos found
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
