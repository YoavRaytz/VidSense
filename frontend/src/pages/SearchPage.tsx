import { useState, useRef } from 'react';
import { searchVideos, ragAnswer, getStreamUrl, getTranscript, getVideoMeta, listTranscripts, type SearchHit, type RAGResponse } from '../api';
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
  
  // Search results
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  
  // RAG answer
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  
  // Video detail view state
  const [selectedVideo, setSelectedVideo] = useState<VideoDetail | null>(null);
  const [streamUrl, setStreamUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [clip, setClip] = useState(1);
  
  // Metadata visibility toggle
  const [showMetadata, setShowMetadata] = useState(true);
  
  // References for scrolling
  const sourceRefs = useRef<{[key: string]: HTMLDivElement | null}>({});

  async function handleSearch() {
    if (!query.trim()) return;
    
    setSearching(true);
    setSearchQuery(query);
    setRagResponse(null);
    setSelectedVideo(null);
    
    try {
      const result = await searchVideos(query, 10);
      setSearchResults(result.hits);
    } catch (e) {
      console.error('Search failed:', e);
      alert(`Search failed: ${e}`);
    } finally {
      setSearching(false);
    }
  }

  async function handleGenerateAnswer() {
    if (!query.trim()) return;
    
    setGenerating(true);
    
    try {
      const result = await ragAnswer(query, 20, 5);
      setRagResponse(result);
      
      // Also run search if we haven't yet
      if (!searchResults.length) {
        const searchResult = await searchVideos(query, 10);
        setSearchResults(searchResult.hits);
      }
    } catch (e) {
      console.error('RAG generation failed:', e);
      alert(`Answer generation failed: ${e}`);
    } finally {
      setGenerating(false);
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
        
        <div className="row" style={{ gap: 12 }}>
          <button
            className="btn btn-primary"
            onClick={handleSearch}
            disabled={!query.trim() || searching || generating}
          >
            {searching ? 'Searching...' : '🔍 Search'}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleGenerateAnswer}
            disabled={!query.trim() || searching || generating}
          >
            {generating ? 'Generating...' : '✨ Generate AI Answer'}
          </button>
        </div>
      </div>

      {/* RAG Answer */}
      {ragResponse && (
        <div className="card" style={{ background: 'linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)', border: '1px solid #2563eb' }}>
          <div className="row" style={{ marginBottom: 12, alignItems: 'center' }}>
            <h3 className="section-title" style={{ margin: 0, color: '#93c5fd' }}>✨ AI Answer</h3>
            <span className="muted" style={{ fontSize: 13 }}>
              Based on {ragResponse.sources.length} source{ragResponse.sources.length > 1 ? 's' : ''}
            </span>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
