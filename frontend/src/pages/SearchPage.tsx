import { useState, useRef } from 'react';
import { searchVideos, ragAnswer, getStreamUrl, getTranscript, getVideoMeta, listTranscripts, saveCollection, saveRetrievalFeedback, deleteRetrievalFeedback, getRetrievalFeedback, findSimilarCollections, type SearchHit, type RAGResponse, type SimilarCollectionResult } from '../api';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptViewer from '../components/TranscriptViewer';
import VideoMetadata from '../components/VideoMetadata';
import ReactMarkdown from 'react-markdown';

interface VideoDetail extends SearchHit {
  clip_count: number;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generateAnswer, setGenerateAnswer] = useState(true); // Checkbox state - default true
  
  // Search results
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Similar collections
  const [similarCollections, setSimilarCollections] = useState<SimilarCollectionResult[]>([]);
  const [expandedCollectionIds, setExpandedCollectionIds] = useState<Set<string>>(new Set());
  const [similarCollectionsExpanded, setSimilarCollectionsExpanded] = useState(true); // Collapse entire section
  
  // RAG answer
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  
  // Video detail view state
  const [selectedVideo, setSelectedVideo] = useState<VideoDetail | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [clip, setClip] = useState(1);
  
  // Metadata visibility toggle
  const [showMetadata, setShowMetadata] = useState(true);
  
  // Retrieval feedback state
  const [feedback, setFeedback] = useState<{[videoId: string]: 'good' | 'bad' | null}>({});
  const [feedbackSubmitting, setFeedbackSubmitting] = useState<{[videoId: string]: boolean}>({});
  
  // Collection feedback state (keyed by collectionId-videoId)
  const [collectionFeedback, setCollectionFeedback] = useState<{[key: string]: 'good' | 'bad' | null}>({});
  const [collectionFeedbackSubmitting, setCollectionFeedbackSubmitting] = useState<{[key: string]: boolean}>({});
  
  // References for scrolling
  const sourceRefs = useRef<{[key: string]: HTMLDivElement | null}>({});

  function handleFeedback(videoId: string, feedbackType: 'good' | 'bad') {
    // Toggle behavior: if clicking the same feedback, unselect it
    // If clicking opposite feedback, switch to it
    setFeedback(prev => {
      const currentFeedback = prev[videoId] || null; // Normalize undefined to null
      
      console.log(`[handleFeedback] videoId: ${videoId}, feedbackType: ${feedbackType}, currentFeedback: ${currentFeedback}`);
      console.log(`[handleFeedback] Full feedback state before:`, prev);
      
      // If clicking the same feedback type, unselect it (remove from object)
      if (currentFeedback === feedbackType) {
        console.log(`Feedback unselected: ${feedbackType} for video ${videoId}`);
        const newState = { ...prev };
        delete newState[videoId]; // Remove the key entirely instead of setting to null
        console.log(`[handleFeedback] New feedback state:`, newState);
        return newState;
      }
      
      // Otherwise, set to new feedback type
      console.log(`Feedback selected: ${feedbackType} for video ${videoId}`);
      const newState = { ...prev, [videoId]: feedbackType };
      console.log(`[handleFeedback] New feedback state:`, newState);
      return newState;
    });
  }

  async function handleCollectionFeedback(collectionId: string, collectionQuery: string, videoId: string, feedbackType: 'good' | 'bad') {
    const key = `${collectionId}-${videoId}`;
    const currentFeedback = collectionFeedback[key];
    
    console.log(`[handleCollectionFeedback] CALLED`);
    console.log(`  collectionId: ${collectionId}`);
    console.log(`  videoId: ${videoId}`);
    console.log(`  feedbackType: ${feedbackType}`);
    console.log(`  key: ${key}`);
    console.log(`  currentFeedback: ${currentFeedback}`);
    console.log(`  currentFeedback === feedbackType: ${currentFeedback === feedbackType}`);
    console.log(`  Full collectionFeedback state:`, collectionFeedback);
    
    // Toggle behavior: if clicking the same feedback, unselect it (delete)
    if (currentFeedback === feedbackType) {
      console.log(`⚡ TOGGLING OFF: ${feedbackType} for video ${videoId}`);
      
      setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: true }));
      
      try {
        // Delete the feedback from database
        await deleteRetrievalFeedback(collectionQuery, videoId);
        console.log(`✅ API call successful - feedback deleted from DB`);
        
        // Remove from UI state
        setCollectionFeedback(prev => {
          const newState = { ...prev };
          delete newState[key];
          console.log(`✅ State updated - key ${key} deleted. New state:`, newState);
          return newState;
        });
        console.log(`Collection feedback deleted for video ${videoId} in collection ${collectionId}`);
      } catch (e) {
        console.error('❌ Failed to delete collection feedback:', e);
        alert(`Failed to delete feedback: ${e}`);
      } finally {
        setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: false }));
      }
      
      return;
    }
    
    // Otherwise, save or switch to new feedback type
    console.log(`⚡ SAVING/SWITCHING: ${feedbackType} for video ${videoId}`);
    setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: true }));
    
    try {
      await saveRetrievalFeedback(collectionQuery, videoId, feedbackType);
      console.log(`✅ API call successful - feedback saved to DB`);
      setCollectionFeedback(prev => {
        const newState = { ...prev, [key]: feedbackType };
        console.log(`✅ State updated - key ${key} = ${feedbackType}. New state:`, newState);
        return newState;
      });
      console.log(`Collection feedback saved: ${feedbackType} for video ${videoId} in collection ${collectionId}`);
    } catch (e) {
      console.error('Failed to save collection feedback:', e);
      alert(`Failed to save feedback: ${e}`);
    } finally {
      setCollectionFeedbackSubmitting(prev => ({ ...prev, [key]: false }));
    }
  }

  async function handleSearch() {
    if (!query.trim()) return;
    
    setSearching(true);
    setSearchQuery(query);
    setRagResponse(null);
    setSelectedVideo(null);
    setSimilarCollections([]);
    setFeedback({}); // Reset feedback for new search - only saved collections keep feedback
    
    try {
      // Find similar collections
      const collectionsResult = await findSimilarCollections(query, 10, 50);
      console.log(`Found ${collectionsResult.collections.length} similar collections`);
      setSimilarCollections(collectionsResult.collections);
      
      // Auto-expand the first (most similar) collection if found
      if (collectionsResult.collections.length > 0) {
        const firstCollection = collectionsResult.collections[0];
        setExpandedCollectionIds(new Set([firstCollection.id]));
        
        // Load feedback for the first collection
        if (firstCollection.videos.length > 0) {
          try {
            const videoIds = firstCollection.videos.map(v => v.id);
            const feedbackResponse = await getRetrievalFeedback(firstCollection.query, videoIds);
            
            const newFeedback: {[key: string]: 'good' | 'bad' | null} = {};
            feedbackResponse.feedback.forEach(fb => {
              const key = `${firstCollection.id}-${fb.video_id}`;
              newFeedback[key] = fb.feedback;
            });
            
            setCollectionFeedback(newFeedback);
            console.log(`[search] Loaded ${feedbackResponse.feedback.length} feedback records for first collection`);
          } catch (error) {
            console.error('[search] Failed to load feedback for first collection:', error);
          }
        }
      }
      
      // If generateAnswer is checked AND no similar collections found, generate new answer automatically
      if (generateAnswer && collectionsResult.collections.length === 0) {
        setGenerating(true);
        try {
          // Pass empty array since no similar collections
          const result = await ragAnswer(query, 20, 5, []);
          setRagResponse(result);
          
          // Don't load existing feedback - feedback should only be visible after collection is saved
          // User will set feedback during this session, and it will be saved when they save the collection
        } catch (e) {
          console.error('RAG generation failed:', e);
          alert(`Answer generation failed: ${e}`);
        } finally {
          setGenerating(false);
        }
      }
      
      // Also get search results if we don't have collections
      if (collectionsResult.collections.length === 0) {
        const searchResult = await searchVideos(query, 10);
        setSearchResults(searchResult.hits);
      }
    } catch (e) {
      console.error('Search failed:', e);
      alert(`Search failed: ${e}`);
    } finally {
      setSearching(false);
    }
  }

  async function handleGenerateNewAnswer() {
    if (!query.trim()) return;
    
    setGenerating(true);
    
    try {
      // Pass similar collection IDs to use their feedback
      const collectionIds = similarCollections.map(c => c.id);
      console.log(`[handleGenerateNewAnswer] Calling ragAnswer with ${collectionIds.length} collection IDs:`, collectionIds);
      const result = await ragAnswer(query, 20, 5, collectionIds);
      setRagResponse(result);
      
      // Don't load existing feedback - feedback should only be visible after collection is saved
      // User will set feedback during this session, and it will be saved when they save the collection
    } catch (e) {
      console.error('RAG generation failed:', e);
      alert(`Answer generation failed: ${e}`);
    } finally {
      setGenerating(false);
    }
  }

  async function toggleCollectionExpand(collectionId: string) {
    const isExpanding = !expandedCollectionIds.has(collectionId);
    
    setExpandedCollectionIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(collectionId)) {
        newSet.delete(collectionId);
      } else {
        newSet.add(collectionId);
      }
      return newSet;
    });
    
    // Load feedback when expanding
    if (isExpanding) {
      const collection = similarCollections.find(c => c.id === collectionId);
      if (collection && collection.videos.length > 0) {
        try {
          const videoIds = collection.videos.map(v => v.id);
          const feedbackResponse = await getRetrievalFeedback(collection.query, videoIds);
          
          // Store feedback with collectionId-videoId key
          const newFeedback: {[key: string]: 'good' | 'bad' | null} = {};
          feedbackResponse.feedback.forEach(fb => {
            const key = `${collectionId}-${fb.video_id}`;
            newFeedback[key] = fb.feedback;
          });
          
          setCollectionFeedback(prev => ({ ...prev, ...newFeedback }));
          console.log(`[collection] Loaded ${feedbackResponse.feedback.length} feedback records for collection ${collectionId}`);
        } catch (error) {
          console.error('[collection] Failed to load feedback:', error);
        }
      }
    }
  }

  async function handleSaveCollection() {
    if (!ragResponse) return;
    
    setSaving(true);
    
    try {
      const videoIds = ragResponse.sources.map(s => s.video_id);
      // Store sources with their scores and order
      const sourcesData = ragResponse.sources.map((s, idx) => ({
        video_id: s.video_id,
        title: s.title,
        author: s.author,
        url: s.url,
        snippet: s.snippet,
        score: s.score,
        order: idx,
      }));
      
      await saveCollection(query, ragResponse.answer, videoIds, {
        sources: sourcesData,
        sources_count: ragResponse.sources.length,
        search_query: searchQuery,
      });
      
      // Now save all the feedback for videos in this collection
      const feedbackPromises = Object.entries(feedback)
        .filter(([videoId, feedbackType]) => {
          // Only save feedback that is not null and for videos in this collection
          return feedbackType !== null && videoIds.includes(videoId);
        })
        .map(([videoId, feedbackType]) => {
          console.log(`Saving feedback for video ${videoId}: ${feedbackType}`);
          return saveRetrievalFeedback(query, videoId, feedbackType as 'good' | 'bad');
        });
      
      if (feedbackPromises.length > 0) {
        await Promise.all(feedbackPromises);
        console.log(`Saved ${feedbackPromises.length} feedback records with collection`);
      }
      
      alert('✅ Collection saved successfully!');
    } catch (e) {
      console.error('Save failed:', e);
      alert(`Failed to save collection: ${e}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleVideoClick(hit: SearchHit) {
    try {
      // Get full video metadata from list endpoint
      const videos = await listTranscripts();
      const fullVideo = videos.find(v => v.id === hit.video_id);
      
      const videoDetail: VideoDetail = fullVideo ? {
        ...hit,
        ...fullVideo,
        clip_count: fullVideo.clip_count || 1,
      } : {
        ...hit,
        clip_count: 1,
      };
      
      setSelectedVideo(videoDetail);
      setClip(1);
      
      // Load stream URL for first clip
      const stream = await getStreamUrl(hit.video_id, 1);
      setStreamUrl(stream.url);
      
      // Load transcript
      const t = await getTranscript(hit.video_id);
      setTranscript(t.text || '');
    } catch (e) {
      console.error('Failed to load video:', e);
      alert(`Failed to load video: ${e}`);
    }
  }

  async function handleClipChange(newClip: number) {
    if (!selectedVideo) return;
    setClip(newClip);
    
    try {
      const stream = await getStreamUrl(selectedVideo.video_id, newClip);
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
  }

  function handleCitationClick(sourceNumber: number) {
    if (!ragResponse) return;
    
    const source = ragResponse.sources[sourceNumber - 1];
    if (!source) return;
    
    // Scroll to the source card
    const ref = sourceRefs.current[source.video_id];
    if (ref) {
      ref.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Highlight briefly
      ref.style.borderColor = '#3b82f6';
      ref.style.boxShadow = '0 0 20px rgba(59, 130, 246, 0.5)';
      setTimeout(() => {
        ref.style.borderColor = '#1f2937';
        ref.style.boxShadow = '';
      }, 2000);
    }
  }

  function renderAnswerWithCitations(answer: string) {
    // Function to recursively process children and make citations clickable
    const makeInteractive = (node: any): any => {
      if (typeof node === 'string') {
        // Split text by citation pattern and make clickable
        const parts = node.split(/(\[\d+\])/g);
        return parts.map((part: string, idx: number) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const citationNum = parseInt(match[1]);
            return (
              <span
                key={`cite-${idx}`}
                onClick={() => handleCitationClick(citationNum)}
                style={{
                  color: '#60a5fa',
                  cursor: 'pointer',
                  fontWeight: 600,
                  textDecoration: 'underline',
                  padding: '0 2px',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#3b82f6')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#60a5fa')}
              >
                {part}
              </span>
            );
          }
          return part;
        });
      }
      
      if (Array.isArray(node)) {
        return node.map((child, idx) => (
          <span key={idx}>{makeInteractive(child)}</span>
        ));
      }
      
      return node;
    };

    return (
      <div style={{ lineHeight: 1.8, color: '#e5e7eb' }}>
        <ReactMarkdown
          components={{
            p: ({ node, children, ...props }) => (
              <p {...props} style={{ marginBottom: '0.75rem', marginTop: 0 }}>
                {makeInteractive(children)}
              </p>
            ),
            strong: ({ node, children, ...props }) => (
              <strong {...props} style={{ color: '#fbbf24', fontWeight: 700 }}>
                {makeInteractive(children)}
              </strong>
            ),
            em: ({ node, children, ...props }) => (
              <em {...props}>{makeInteractive(children)}</em>
            ),
            li: ({ node, children, ...props }) => (
              <li {...props} style={{ marginBottom: '0.5rem', lineHeight: 1.6 }}>
                {makeInteractive(children)}
              </li>
            ),
            ul: ({ node, children, ...props }) => (
              <ul {...props} style={{ 
                marginLeft: '1.5rem', 
                marginTop: '0.5rem', 
                marginBottom: '0.75rem', 
                paddingLeft: '0.5rem',
                listStyleType: 'disc'
              }}>
                {children}
              </ul>
            ),
            ol: ({ node, children, ...props }) => (
              <ol {...props} style={{ 
                marginLeft: '1.5rem', 
                marginTop: '0.5rem', 
                marginBottom: '0.75rem', 
                paddingLeft: '0.5rem'
              }}>
                {children}
              </ol>
            ),
          }}
        >
          {answer}
        </ReactMarkdown>
      </div>
    );
  }

  // Detail view (when video is selected)
  if (selectedVideo) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Back button */}
        <div className="card">
          <button className="btn" onClick={handleBack}>
            ← Back to Search Results
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
              videoId={selectedVideo.video_id}
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

  // Search interface (when no video selected)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Search Box */}
      <div className="card">
        <h3 className="section-title">🔍 Search Your Videos</h3>
        <p className="muted" style={{ marginBottom: 16 }}>
          Search across all video transcripts and captions using semantic similarity
        </p>
        
        <div className="row" style={{ marginBottom: 12 }}>
          <input
            className="input"
            placeholder="Ask a question or search for topics..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            disabled={searching || generating}
          />
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={handleSearch}
              disabled={!query.trim() || searching || generating}
            >
              {searching || generating ? '⏳ Processing...' : '🔍 Search'}
            </button>
            
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={generateAnswer}
                onChange={(e) => setGenerateAnswer(e.target.checked)}
                style={{ cursor: 'pointer', width: 18, height: 18 }}
              />
              <span style={{ fontSize: 14, color: '#d1d5db' }}>✨ Generate AI Answer</span>
            </label>
          </div>
        </div>
      </div>

      {/* RAG Answer */}
      {ragResponse && (
        <div className="card" style={{ background: 'linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)', border: '1px solid #2563eb' }}>
          <div className="row" style={{ marginBottom: 12, justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="row" style={{ alignItems: 'center', gap: 12 }}>
              <h3 className="section-title" style={{ margin: 0, color: '#93c5fd' }}>✨ AI Answer</h3>
              <span className="muted" style={{ fontSize: 13 }}>
                Based on {ragResponse.sources.length} source{ragResponse.sources.length > 1 ? 's' : ''}
              </span>
            </div>
            
            <button
              className="btn"
              onClick={handleSaveCollection}
              disabled={saving}
              style={{
                background: '#10b981',
                border: 'none',
                padding: '8px 16px',
                fontSize: 14,
                fontWeight: 600,
              }}
              onMouseEnter={(e) => {
                if (!saving) e.currentTarget.style.background = '#059669';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#10b981';
              }}
            >
              {saving ? '💾 Saving...' : '💾 Save to Collections'}
            </button>
          </div>
          
          <div style={{
            background: '#0b1220',
            border: '1px solid #1f2937',
            borderRadius: 8,
            padding: 16,
            marginBottom: 16
          }}>
            {renderAnswerWithCitations(ragResponse.answer)}
          </div>
          
          <p className="muted" style={{ fontSize: 12, margin: 0 }}>
            💡 Click on citations [1], [2], etc. to jump to source videos below
          </p>
        </div>
      )}

      {/* Similar Collections Found */}
      {similarCollections.length > 0 && (
        <div className="card" style={{ background: '#1e293b', border: '1px solid #3b82f6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <h3 className="section-title" style={{ color: '#60a5fa', marginBottom: 8 }}>
                💡 Similar Past Searches Found
              </h3>
              <p className="muted" style={{ fontSize: 14 }}>
                The system detected {similarCollections.length} previous search{similarCollections.length > 1 ? 'es' : ''} that might be what you're looking for
              </p>
            </div>
            
            <button
              onClick={() => setSimilarCollectionsExpanded(!similarCollectionsExpanded)}
              style={{
                padding: '8px 16px',
                background: '#2563eb',
                border: 'none',
                borderRadius: 6,
                color: 'white',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 500,
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#1d4ed8';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
            >
              {similarCollectionsExpanded ? '▲ Collapse All' : '▼ Expand All'}
            </button>
          </div>

          {similarCollectionsExpanded && (
            <>
              {!ragResponse && (
                <button
                  className="btn btn-primary"
                  onClick={handleGenerateNewAnswer}
                  disabled={generating}
                  style={{
                    marginBottom: 16,
                    background: '#2563eb',
                    fontSize: 14,
                  }}
                  onMouseEnter={(e) => {
                    if (!generating) e.currentTarget.style.background = '#1d4ed8';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#2563eb';
                  }}
                >
                  {generating ? '⏳ Generating...' : '✨ Generate New Answer Anyway'}
                </button>
              )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {similarCollections.map((collection, idx) => (
              <div
                key={collection.id}
                style={{
                  background: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: 8,
                  padding: 16,
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#3b82f6';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#334155';
                }}
              >
                {/* Collection Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 12,
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{
                        background: '#2563eb',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: 4,
                        fontSize: 12,
                        fontWeight: 600,
                      }}>
                        {(collection.similarity * 100).toFixed(0)}% match
                      </span>
                      <h4 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
                        {collection.query}
                      </h4>
                    </div>
                    <p className="muted" style={{ fontSize: 13, margin: 0 }}>
                      Saved {new Date(collection.created_at).toLocaleDateString()}
                      {' • '}
                      {collection.videos.length} source{collection.videos.length !== 1 ? 's' : ''}
                    </p>
                  </div>

                  <button
                    onClick={() => toggleCollectionExpand(collection.id)}
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
                    {expandedCollectionIds.has(collection.id) ? '▲ Collapse' : '▼ Expand'}
                  </button>
                </div>

                {/* Expanded Content */}
                {expandedCollectionIds.has(collection.id) && (
                  <>
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
                        <div style={{ fontSize: 14, lineHeight: 1.6 }}>
                          <ReactMarkdown>{collection.ai_answer}</ReactMarkdown>
                        </div>
                      </div>
                    )}

                    {/* Sources */}
                    {collection.videos.length > 0 && (
                      <>
                        <h4 style={{
                          fontSize: 14,
                          fontWeight: 600,
                          marginBottom: 12,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                        }}>
                          <span>📚</span>
                          <span>Sources ({collection.videos.length})</span>
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                          {collection.videos.map((video, vidIdx) => {
                            const feedbackKey = `${collection.id}-${video.id}`;
                            const videoFeedback = collectionFeedback[feedbackKey];
                            const isSubmitting = collectionFeedbackSubmitting[feedbackKey];
                            
                            console.log(`[Render] Collection video ${video.id}: feedbackKey=${feedbackKey}, videoFeedback=${videoFeedback}, isSubmitting=${isSubmitting}`);
                            
                            return (
                            <div
                              key={video.id}
                              onClick={() => {
                                // Handle video click - convert to SearchHit format
                                const hit: SearchHit = {
                                  video_id: video.id,
                                  title: video.title,
                                  author: video.author,
                                  url: video.url,
                                  score: video.score || 0,
                                  snippet: video.snippet || video.description || '',
                                  media_path: null,
                                  source: null,
                                  description: video.description
                                };
                                handleVideoClick(hit);
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#3b82f6';
                                e.currentTarget.style.background = '#1f2937';
                                const feedbackButtons = e.currentTarget.querySelector('.collection-feedback-buttons') as HTMLElement;
                                if (feedbackButtons) feedbackButtons.style.opacity = '1';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#334155';
                                e.currentTarget.style.background = '#1e293b';
                                const feedbackButtons = e.currentTarget.querySelector('.collection-feedback-buttons') as HTMLElement;
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
                                className="collection-feedback-buttons"
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.opacity = '1';
                                }}
                              >
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleCollectionFeedback(collection.id, collection.query, video.id, 'good');
                                  }}
                                  disabled={isSubmitting}
                                  style={{
                                    background: videoFeedback === 'good' ? '#10b981' : '#1f2937',
                                    border: '1px solid ' + (videoFeedback === 'good' ? '#10b981' : '#374151'),
                                    color: videoFeedback === 'good' ? 'white' : '#9ca3af',
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    cursor: isSubmitting ? 'wait' : 'pointer',
                                    fontSize: 14,
                                    lineHeight: 1,
                                    transition: 'all 0.2s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    if (videoFeedback !== 'good') {
                                      e.currentTarget.style.background = '#10b981';
                                      e.currentTarget.style.borderColor = '#10b981';
                                      e.currentTarget.style.color = 'white';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (videoFeedback !== 'good') {
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
                                    handleCollectionFeedback(collection.id, collection.query, video.id, 'bad');
                                  }}
                                  disabled={isSubmitting}
                                  style={{
                                    background: videoFeedback === 'bad' ? '#ef4444' : '#1f2937',
                                    border: '1px solid ' + (videoFeedback === 'bad' ? '#ef4444' : '#374151'),
                                    color: videoFeedback === 'bad' ? 'white' : '#9ca3af',
                                    padding: '4px 8px',
                                    borderRadius: 4,
                                    cursor: isSubmitting ? 'wait' : 'pointer',
                                    fontSize: 14,
                                    lineHeight: 1,
                                    transition: 'all 0.2s ease',
                                  }}
                                  onMouseEnter={(e) => {
                                    if (videoFeedback !== 'bad') {
                                      e.currentTarget.style.background = '#ef4444';
                                      e.currentTarget.style.borderColor = '#ef4444';
                                      e.currentTarget.style.color = 'white';
                                    }
                                  }}
                                  onMouseLeave={(e) => {
                                    if (videoFeedback !== 'bad') {
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
                                    [{vidIdx + 1}]
                                  </span>
                                  <h4 style={{ margin: 0, fontSize: 16 }}>
                                    {video.title || 'Untitled Video'}
                                  </h4>
                                </div>
                                {video.score && (
                                  <span style={{
                                    color: '#10b981',
                                    fontSize: 13,
                                    fontWeight: 600,
                                  }}>
                                    {(video.score * 100).toFixed(1)}% match
                                  </span>
                                )}
                              </div>

                              {video.author && (
                                <p className="muted" style={{ margin: '4px 0 8px 0', fontSize: 13 }}>
                                  by {video.author}
                                </p>
                              )}

                              {(video.description || video.snippet) && (
                                <p style={{
                                  fontSize: 14,
                                  lineHeight: 1.6,
                                  color: '#d1d5db',
                                  margin: '8px 0 0 0',
                                }}>
                                  {(video.description || video.snippet)!.length > 200
                                    ? (video.description || video.snippet)!.slice(0, 200) + '...'
                                    : (video.description || video.snippet)}
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
                            );
                          })}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
            </>
          )}
        </div>
      )}

      {/* Search Results or Sources */}
      {(searchResults.length > 0 || ragResponse) && (
        <div className="card">
          <h3 className="section-title">
            {ragResponse ? `📚 Sources (${ragResponse.sources.length})` : `📊 Results (${searchResults.length})`}
          </h3>
          
          {ragResponse ? (
            /* Show sources used in RAG answer */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {ragResponse.sources.map((source, idx) => (
                <div
                  key={source.video_id}
                  ref={(el) => (sourceRefs.current[source.video_id] = el)}
                  onClick={() => {
                    const hit: SearchHit = {
                      video_id: source.video_id,
                      title: source.title,
                      author: source.author,
                      url: source.url,
                      score: source.score,
                      snippet: source.snippet,
                      media_path: null,
                      source: null,
                      description: null
                    };
                    handleVideoClick(hit);
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#3b82f6';
                    e.currentTarget.style.background = '#0f1420';
                    const feedbackButtons = e.currentTarget.querySelector('.feedback-buttons') as HTMLElement;
                    if (feedbackButtons) feedbackButtons.style.opacity = '1';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#1f2937';
                    e.currentTarget.style.background = '#0b1220';
                    const feedbackButtons = e.currentTarget.querySelector('.feedback-buttons') as HTMLElement;
                    if (feedbackButtons) feedbackButtons.style.opacity = '0';
                  }}
                  style={{
                    padding: 16,
                    background: '#0b1220',
                    border: '1px solid #1f2937',
                    borderRadius: 8,
                    position: 'relative',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
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
                        handleFeedback(source.video_id, 'good');
                      }}
                      disabled={feedbackSubmitting[source.video_id]}
                      style={{
                        background: feedback[source.video_id] === 'good' ? '#10b981' : '#1f2937',
                        border: '1px solid ' + (feedback[source.video_id] === 'good' ? '#10b981' : '#374151'),
                        color: feedback[source.video_id] === 'good' ? 'white' : '#9ca3af',
                        padding: '4px 8px',
                        borderRadius: 4,
                        cursor: feedbackSubmitting[source.video_id] ? 'wait' : 'pointer',
                        fontSize: 14,
                        lineHeight: 1,
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (feedback[source.video_id] !== 'good') {
                          e.currentTarget.style.background = '#10b981';
                          e.currentTarget.style.borderColor = '#10b981';
                          e.currentTarget.style.color = 'white';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (feedback[source.video_id] !== 'good') {
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
                        handleFeedback(source.video_id, 'bad');
                      }}
                      disabled={feedbackSubmitting[source.video_id]}
                      style={{
                        background: feedback[source.video_id] === 'bad' ? '#ef4444' : '#1f2937',
                        border: '1px solid ' + (feedback[source.video_id] === 'bad' ? '#ef4444' : '#374151'),
                        color: feedback[source.video_id] === 'bad' ? 'white' : '#9ca3af',
                        padding: '4px 8px',
                        borderRadius: 4,
                        cursor: feedbackSubmitting[source.video_id] ? 'wait' : 'pointer',
                        fontSize: 14,
                        lineHeight: 1,
                        transition: 'all 0.2s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (feedback[source.video_id] !== 'bad') {
                          e.currentTarget.style.background = '#ef4444';
                          e.currentTarget.style.borderColor = '#ef4444';
                          e.currentTarget.style.color = 'white';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (feedback[source.video_id] !== 'bad') {
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

                  {/* Video card content */}
                  <div>
                    <div className="row" style={{ marginBottom: 8, justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                        <span style={{
                          background: '#2563eb',
                          color: 'white',
                          padding: '4px 8px',
                          borderRadius: 4,
                          fontSize: 12,
                          fontWeight: 600
                        }}>
                          [{idx + 1}]
                        </span>
                        <h4 style={{ margin: 0, fontSize: 16 }}>{source.title || 'Untitled Video'}</h4>
                        
                        {/* Source type badge */}
                        {source.source_type && source.source_type !== 'search' && (
                          <span style={{
                            background: source.source_type === 'collection' ? '#10b981' : '#f59e0b',
                            color: 'white',
                            padding: '3px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 600,
                          }}
                          title={source.source_reference || undefined}
                          >
                            {source.source_type === 'collection' ? '📁 From Collection' : '⭐ From Feedback'}
                            {source.source_reference && `: "${source.source_reference}"`}
                          </span>
                        )}
                      </div>
                      <span style={{
                        color: '#10b981',
                        fontSize: 13,
                        fontWeight: 600
                      }}>
                        {(source.score * 100).toFixed(1)}% match
                      </span>
                    </div>
                    
                    {source.author && (
                      <p className="muted" style={{ margin: '4px 0 8px 0', fontSize: 13 }}>
                        by {source.author}
                      </p>
                    )}
                    
                    <p style={{
                      fontSize: 14,
                      lineHeight: 1.6,
                      color: '#d1d5db',
                      margin: 0
                    }}>
                      {source.snippet}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Show regular search results */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {searchResults.map((hit) => (
                <div
                  key={hit.video_id}
                  onClick={() => handleVideoClick(hit)}
                  style={{
                    padding: 16,
                    background: '#0b1220',
                    border: '1px solid #1f2937',
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#3b82f6';
                    e.currentTarget.style.background = '#0f1420';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#1f2937';
                    e.currentTarget.style.background = '#0b1220';
                  }}
                >
                  <div className="row" style={{ marginBottom: 8, justifyContent: 'space-between' }}>
                    <h4 style={{ margin: 0, fontSize: 16 }}>{hit.title || 'Untitled Video'}</h4>
                    <span style={{
                      color: '#10b981',
                      fontSize: 13,
                      fontWeight: 600
                    }}>
                      {(hit.score * 100).toFixed(1)}% match
                    </span>
                  </div>
                  
                  {hit.author && (
                    <p className="muted" style={{ margin: '4px 0 8px 0', fontSize: 13 }}>
                      by {hit.author}
                    </p>
                  )}
                  
                  <p style={{
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: '#d1d5db',
                    margin: 0
                  }}>
                    {hit.snippet}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Excluded Videos Section */}
      {ragResponse && ragResponse.excluded_videos && ragResponse.excluded_videos.length > 0 && (
        <div className="card" style={{ background: '#1e1b26', border: '1px solid #4b5563' }}>
          <details>
            <summary style={{
              cursor: 'pointer',
              fontSize: 16,
              fontWeight: 600,
              color: '#9ca3af',
              userSelect: 'none',
              padding: '4px 0',
            }}>
              🚫 Excluded from Search ({ragResponse.excluded_videos.length} videos)
            </summary>
            
            <p className="muted" style={{ fontSize: 13, marginTop: 12, marginBottom: 16 }}>
              These videos were excluded from the new search to optimize performance. 
              They were already known from similar collections or past feedback.
            </p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
              {ragResponse.excluded_videos.map((excluded) => (
                <div
                  key={excluded.video_id}
                  style={{
                    padding: 12,
                    background: '#0f0d14',
                    border: '1px solid #374151',
                    borderRadius: 6,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
                    <div style={{ flex: 1 }}>
                      <h5 style={{ margin: '0 0 4px 0', fontSize: 14, color: '#d1d5db' }}>
                        {excluded.title || 'Untitled Video'}
                      </h5>
                      <p className="muted" style={{ fontSize: 12, margin: 0 }}>
                        {excluded.video_id}
                      </p>
                    </div>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                      {/* Reason badge */}
                      <span style={{
                        background: excluded.reason === 'liked_in_collection' ? '#10b981' : 
                                   excluded.reason === 'disliked_in_collection' ? '#ef4444' : '#f59e0b',
                        color: 'white',
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}>
                        {excluded.reason === 'liked_in_collection' ? '👍 Liked' :
                         excluded.reason === 'disliked_in_collection' ? '👎 Disliked' : '⚠️ Bad Feedback'}
                      </span>
                      
                      {/* Reference */}
                      {excluded.source_reference && excluded.source_reference !== 'similar_query' && (
                        <span style={{
                          fontSize: 11,
                          color: '#9ca3af',
                          fontStyle: 'italic',
                          textAlign: 'right',
                        }}>
                          from: "{excluded.source_reference}"
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* Empty State */}
      {!searching && !generating && !searchResults.length && !ragResponse && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <p className="muted" style={{ fontSize: 16 }}>
            🎬 Start searching to find relevant videos from your collection
          </p>
          <p className="muted" style={{ fontSize: 14, marginTop: 8 }}>
            Try asking questions or searching for specific topics
          </p>
        </div>
      )}
    </div>
  );
}
