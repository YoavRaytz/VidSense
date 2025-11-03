import React from 'react';
import { VideoSummary } from '../api';

interface VideoMetadataProps {
  video: Partial<VideoSummary>;
  showToggle?: boolean;
  onToggleVisibility?: (visible: boolean) => void;
  initiallyVisible?: boolean;
}

export default function VideoMetadata({ 
  video, 
  showToggle = false, 
  onToggleVisibility,
  initiallyVisible = true 
}: VideoMetadataProps) {
  const [isVisible, setIsVisible] = React.useState(initiallyVisible);

  const handleToggle = (visible: boolean) => {
    setIsVisible(visible);
    onToggleVisibility?.(visible);
  };

  // Extract platform info
  const platform = video.metadata_json?.platform || 'web';
  const platformEmoji = {
    instagram: '📷',
    youtube: '▶️',
    tiktok: '🎵',
    twitter: '🐦',
    facebook: '👥',
    web: '🌐'
  }[platform.toLowerCase()] || '🌐';

  // Format duration
  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Get profile URL from metadata or fallback to URL extraction
  const getProfileUrl = () => {
    // First priority: use uploader_url or channel_url from metadata
    if (video.metadata_json?.uploader_url) {
      return video.metadata_json.uploader_url;
    }
    if (video.metadata_json?.channel_url) {
      return video.metadata_json.channel_url;
    }
    
    // Fallback: Extract from URL (Instagram-specific for backward compatibility)
    if (video.url?.includes('instagram.com')) {
      const urlMatch = video.url.match(/instagram\.com\/([^/]+)/);
      if (urlMatch && urlMatch[1] !== 'reel' && urlMatch[1] !== 'p') {
        return `https://www.instagram.com/${urlMatch[1]}/`;
      }
      
      // Try to extract from author name
      if (video.author) {
        const cleanAuthor = video.author.split('|')[0].trim().toLowerCase().replace(/[^a-z0-9._]/g, '');
        if (cleanAuthor) {
          return `https://www.instagram.com/${cleanAuthor}/`;
        }
      }
    }
    
    return null;
  };

  const profileUrl = getProfileUrl();
  const duration = formatDuration(video.duration_sec);
  const likeCount = video.metadata_json?.like_count;
  const commentCount = video.metadata_json?.comment_count;
  const viewCount = video.metadata_json?.view_count;

  const hasStats = likeCount || commentCount || viewCount || duration;

  if (!video.description && !video.author && !hasStats && (!video.hashtags || video.hashtags.length === 0)) {
    return null; // Don't render if no metadata to show
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h3 className="section-title" style={{ margin: 0 }}>📹 Video Info & Stats</h3>
        {showToggle && (
          <label className="text-xs text-gray-600" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input 
              type="checkbox" 
              checked={isVisible} 
              onChange={e => handleToggle(e.target.checked)} 
            />
            Show info
          </label>
        )}
      </div>
      
      {isVisible && (
        <div style={{ 
          background: '#0b1220', 
          border: '1px solid #1f2937', 
          borderRadius: 8, 
          padding: 16 
        }}>
          {/* Platform & Author */}
          {(video.author || platform !== 'web') && (
            <div style={{ 
              marginBottom: 12, 
              paddingBottom: 12, 
              borderBottom: '1px solid #1f2937',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexWrap: 'wrap'
            }}>
              <span style={{ 
                background: '#1f2937', 
                padding: '4px 10px', 
                borderRadius: 6, 
                fontSize: 13,
                fontWeight: 600,
                textTransform: 'capitalize'
              }}>
                {platformEmoji} {platform}
              </span>
              
              {video.author && (
                <>
                  <span style={{ color: '#6b7280' }}>•</span>
                  {profileUrl ? (
                    <a 
                      href={profileUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ 
                        color: '#60a5fa', 
                        textDecoration: 'none',
                        fontWeight: 500,
                        fontSize: 14
                      }}
                      onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                      onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
                    >
                      {video.author} 🔗
                    </a>
                  ) : (
                    <span style={{ color: '#e5e7eb', fontWeight: 500, fontSize: 14 }}>
                      {video.author}
                    </span>
                  )}
                </>
              )}
            </div>
          )}

          {/* Engagement Stats */}
          {hasStats && (
            <div style={{ 
              marginBottom: 12, 
              paddingBottom: 12, 
              borderBottom: '1px solid #1f2937',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              flexWrap: 'wrap',
              fontSize: 14,
              color: '#9ca3af'
            }}>
              {likeCount !== undefined && likeCount !== null && (
                <span>👍 {likeCount.toLocaleString()} likes</span>
              )}
              {commentCount !== undefined && commentCount !== null && (
                <span>💬 {commentCount.toLocaleString()} comments</span>
              )}
              {viewCount !== undefined && viewCount !== null && (
                <span>👁️ {viewCount.toLocaleString()} views</span>
              )}
              {duration && (
                <span>⏱️ {duration}</span>
              )}
            </div>
          )}

          {/* Hashtags */}
          {video.hashtags && video.hashtags.length > 0 && (
            <div style={{ 
              marginBottom: 12, 
              paddingBottom: 12, 
              borderBottom: '1px solid #1f2937',
              display: 'flex',
              gap: 6,
              flexWrap: 'wrap'
            }}>
              {video.hashtags.map((tag, idx) => (
                <span 
                  key={idx} 
                  style={{ 
                    background: '#1e3a8a', 
                    color: '#93c5fd', 
                    padding: '3px 8px', 
                    borderRadius: 4, 
                    fontSize: 12,
                    fontWeight: 500
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Description */}
          {video.description && (
            <div>
              <div style={{ 
                color: '#93c5fd', 
                fontWeight: 600, 
                fontSize: 12, 
                letterSpacing: 0.2, 
                marginBottom: 8,
                textTransform: 'uppercase'
              }}>
                Description
              </div>
              <pre style={{ 
                margin: 0, 
                whiteSpace: 'pre-wrap', 
                wordBreak: 'break-word', 
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace', 
                lineHeight: 1.6, 
                color: '#e5e7eb',
                fontSize: 14
              }}>
                {video.description}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
