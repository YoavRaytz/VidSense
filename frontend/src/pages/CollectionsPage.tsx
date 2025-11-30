import { useEffect, useState } from 'react';
import { getCollections, deleteCollection, getCollection, Collection, CollectionWithVideos, getStreamUrl, getTranscript, listTranscripts, saveRetrievalFeedback, deleteRetrievalFeedback, getRetrievalFeedback, type VideoSummary } from '../api';
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
  
  // Feedback state
  const [feedback, setFeedback] = useState<{[videoId: string]: 'good' | 'bad' | null}>({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState<{[videoId: string]: boolean}>({});
  
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
        
        // Load existing feedback for these videos
        if (fullCollection.videos && fullCollection.videos.length > 0) {
          const videoIds = fullCollection.videos.map(v => v.id);
          try {
            const feedbackResponse = await getRetrievalFeedback(fullCollection.query, videoIds);
            
            // Convert feedback array to object for easy lookup
            const feedbackMap: {[videoId: string]: 'good' | 'bad' | null} = {};
            feedbackResponse.feedback.forEach(fb => {
              feedbackMap[fb.video_id] = fb.feedback;
            });
            
            setFeedback(feedbackMap);
            console.log(`[collections] Loaded ${feedbackResponse.feedback.length} feedback records`);
          } catch (error) {
            console.error('[collections] Failed to load feedback:', error);
            // Continue without feedback - not a critical error
          }
        }
      } catch (err: any) {
        alert('Failed to load collection details: ' + err.message);
        setExpandedId(null);
      } finally {
        setLoadingExpanded(false);
      }
    }
  };

  const handleFeedback = async (videoId: string, feedbackType: 'good' | 'bad') => {
    if (!expandedCollection) return;
    
    const currentFeedback = feedback[videoId];
    
    console.log(`[handleFeedback-CollectionsPage] CALLED`);
    console.log(`  videoId: ${videoId}`);
    console.log(`  feedbackType: ${feedbackType}`);
    console.log(`  currentFeedback: ${currentFeedback}`);
    console.log(`  currentFeedback === feedbackType: ${currentFeedback === feedbackType}`);
    
    // Toggle behavior: if clicking the same feedback, unselect it (delete)
    if (currentFeedback === feedbackType) {
      console.log(`⚡ TOGGLING OFF: ${feedbackType} for video ${videoId}`);
      setFeedbackSubmitting(prev => ({ ...prev, [videoId]: true }));
      
      try {
        await deleteRetrievalFeedback(expandedCollection.query, videoId);
        console.log(`✅ Feedback deleted from DB`);
        setFeedback(prev => {
          const newState = { ...prev };
          delete newState[videoId];
          console.log(`✅ State updated - key ${videoId} deleted`);
          return newState;
        });
      } catch (error) {
        console.error('❌ Failed to delete feedback:', error);
        alert('Failed to delete feedback. Please try again.');
      } finally {
        setFeedbackSubmitting(prev => ({ ...prev, [videoId]: false }));
      }
      return;
    }
    
    // Otherwise, save or switch to new feedback type
    console.log(`⚡ SAVING/SWITCHING: ${feedbackType} for video ${videoId}`);
    setFeedback(prev => ({ ...prev, [videoId]: feedbackType }));
    setFeedbackSubmitting(prev => ({ ...prev, [videoId]: true }));
    
    try {
      await saveRetrievalFeedback(expandedCollection.query, videoId, feedbackType);
      console.log(`✅ Feedback saved: ${feedbackType} for video ${videoId}`);
    } catch (error) {
      console.error('❌ Failed to save feedback:', error);
      // Revert on error
      setFeedback(prev => ({ ...prev, [videoId]: null }));
      alert('Failed to save feedback. Please try again.');
    } finally {
      setFeedbackSubmitting(prev => ({ ...prev, [videoId]: false }));
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
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#3b82f6';
                                e.currentTarget.style.background = '#1f2937';
                                const feedbackButtons = e.currentTarget.querySelector('.feedback-buttons') as HTMLElement;
                                if (feedbackButtons) feedbackButtons.style.opacity = '1';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#334155';
                                e.currentTarget.style.background = '#1e293b';
                                const feedbackButtons = e.currentTarget.querySelector('.feedback-buttons') as HTMLElement;
                                if (feedbackButtons) feedbackButtons.style.opacity = '0';
                              }}
                              style={{
                                padding: 16,
                                background: '#1e293b',
                                border: '1px solid #334155',
                                borderRadius: 8,
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                position: 'relative',
                              }}
                            >
                              {/* Feedback buttons (shown on hover) - positioned on right below match score */}
                              <div
                                style={{
                                  position: 'absolute',
                                  top: 48,
                                  right: 12,
                                  display: 'flex',
                                  gap: 6,
                                  opacity: 0,
                                  transition: 'opacity 0.2s ease',
                                  pointerEvents: 'auto',
                                  zIndex: 10,
                                }}
                                className="feedback-buttons"
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.opacity = '1';
                                }}
                              >
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleFeedback(video.id, 'good');
                                  }}
                                  disabled={feedbackSubmitting[video.id]}
                                  style={{
                                    background: feedback[video.id] === 'good' ? '#10b981' : '#1f2937',
                                    border: '1px solid ' + (feedback[video.id] === 'good' ? '#10b981' : '#374151'),
                                    color: feedback[video.id] === 'good' ? 'white' : '#9ca3af',
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    cursor: feedbackSubmitting[video.id] ? 'wait' : 'pointer',
                                    fontSize: 14,
                                    lineHeight: 1,
                                    transition: 'all 0.2s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    if (feedback[video.id] !== 'good') {
                                      e.currentTarget.style.background = '#10b981';
                                      e.currentTarget.style.borderColor = '#10b981';
                                      e.currentTarget.style.color = 'white';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (feedback[video.id] !== 'good') {
                                      e.currentTarget.style.background = '#1f2937';
                                      e.currentTarget.style.borderColor = '#374151';
                                      e.currentTarget.style.color = '#9ca3af';
                                    }
                                  }}
                                  title="Good retrieve"
                                >
                                  👍
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleFeedback(video.id, 'bad');
                                  }}
                                  disabled={feedbackSubmitting[video.id]}
                                  style={{
                                    background: feedback[video.id] === 'bad' ? '#ef4444' : '#1f2937',
                                    border: '1px solid ' + (feedback[video.id] === 'bad' ? '#ef4444' : '#374151'),
                                    color: feedback[video.id] === 'bad' ? 'white' : '#9ca3af',
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    cursor: feedbackSubmitting[video.id] ? 'wait' : 'pointer',
                                    fontSize: 14,
                                    lineHeight: 1,
                                    transition: 'all 0.2s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    if (feedback[video.id] !== 'bad') {
                                      e.currentTarget.style.background = '#ef4444';
                                      e.currentTarget.style.borderColor = '#ef4444';
                                      e.currentTarget.style.color = 'white';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (feedback[video.id] !== 'bad') {
                                      e.currentTarget.style.background = '#1f2937';
                                      e.currentTarget.style.borderColor = '#374151';
                                      e.currentTarget.style.color = '#9ca3af';
                                    }
                                  }}
                                  title="Bad retrieve"
                                >
                                  👎
                                </button>
                              </div>

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
