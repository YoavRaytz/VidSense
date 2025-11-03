import type { VideoSummary } from '../api';

interface VideoCardProps {
  video: VideoSummary;
  onClick?: () => void;
  onDelete?: (e: React.MouseEvent) => void;
  isHovered?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  showCheckbox?: boolean;
  isSelected?: boolean;
  onToggleSelection?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  showDeleteButton?: boolean;
  compact?: boolean;
}

export default function VideoCard({
  video,
  onClick,
  onDelete,
  isHovered = false,
  onMouseEnter,
  onMouseLeave,
  showCheckbox = false,
  isSelected = false,
  onToggleSelection,
  showDeleteButton = false,
  compact = false,
}: VideoCardProps) {
  
  function formatDate(dateStr?: string | null) {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
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

  function getPlatformEmoji(source: string) {
    const lower = source.toLowerCase();
    if (lower.includes('instagram')) return '📷';
    if (lower.includes('youtube')) return '▶️';
    if (lower.includes('tiktok')) return '🎵';
    if (lower.includes('twitter') || lower.includes('x.com')) return '🐦';
    if (lower.includes('facebook')) return '👥';
    return '🌐';
  }

  function getInstagramProfileUrl(video: VideoSummary): string | null {
    // Extract Instagram username from URL or metadata
    const urlMatch = video.url?.match(/instagram\.com\/([^\/]+)\//);
    if (urlMatch && urlMatch[1] !== 'reel' && urlMatch[1] !== 'p') {
      return `https://www.instagram.com/${urlMatch[1]}/`;
    }
    
    // Try to get from author or metadata
    if (video.author) {
      // Clean author name (remove emojis, special chars, get first part)
      const cleanAuthor = video.author.split('|')[0].trim().toLowerCase().replace(/[^a-z0-9._]/g, '');
      if (cleanAuthor) {
        return `https://www.instagram.com/${cleanAuthor}/`;
      }
    }
    
    return null;
  }

  const platformEmoji = getPlatformEmoji(video.source);
  const instagramProfile = getInstagramProfileUrl(video);
  
  return (
    <div
      onClick={onClick}
      style={{
        padding: compact ? 12 : 16,
        background: '#0b1220',
        border: '1px solid #1f2937',
        borderRadius: 8,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 0.15s ease, background 0.15s ease',
        position: 'relative',
      }}
      onMouseEnter={() => {
        onMouseEnter?.();
        if (onClick) {
          const elem = document.querySelector(`[data-video-id="${video.id}"]`) as HTMLElement;
          if (elem) {
            elem.style.borderColor = '#3b82f6';
            elem.style.background = '#0f1420';
          }
        }
      }}
      onMouseLeave={() => {
        onMouseLeave?.();
        const elem = document.querySelector(`[data-video-id="${video.id}"]`) as HTMLElement;
        if (elem) {
          elem.style.borderColor = '#1f2937';
          elem.style.background = '#0b1220';
        }
      }}
      data-video-id={video.id}
    >
      {/* Header Row */}
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ flex: 1, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          {showCheckbox && onToggleSelection && (
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelection}
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
            {/* Title */}
            <h4 style={{ margin: '0 0 6px 0', fontSize: compact ? 14 : 16, fontWeight: 600 }}>
              {video.title || 'Untitled Video'}
            </h4>
            
            {/* Author with Instagram link */}
            {video.author && (
              <div className="muted" style={{ margin: '0 0 8px 0', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>by</span>
                {instagramProfile ? (
                  <a
                    href={instagramProfile}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      color: '#60a5fa',
                      textDecoration: 'none',
                      fontWeight: 500,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.textDecoration = 'underline')}
                    onMouseLeave={(e) => (e.currentTarget.style.textDecoration = 'none')}
                  >
                    {video.author} 🔗
                  </a>
                ) : (
                  <span style={{ fontWeight: 500 }}>{video.author}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right side actions */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {video.duration_sec && (
            <span className="muted" style={{ fontSize: 12 }}>
              ⏱️ {formatDuration(video.duration_sec)}
            </span>
          )}
          
          {showDeleteButton && isHovered && onDelete && (
            <button
              onClick={onDelete}
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

      {/* Metadata Row */}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {/* Platform badge */}
        <span style={{ 
          fontSize: 11, 
          padding: '3px 10px', 
          background: '#1f2937', 
          borderRadius: 12,
          textTransform: 'capitalize',
          letterSpacing: 0.5,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}>
          <span>{platformEmoji}</span>
          {video.source}
        </span>

        {/* Date */}
        {video.created_at && (
          <span className="muted" style={{ fontSize: 11 }}>
            📅 {formatDate(video.created_at)}
          </span>
        )}

        {/* Clip count for multi-clip videos */}
        {video.clip_count && video.clip_count > 1 && (
          <span className="muted" style={{ fontSize: 11 }}>
            📚 {video.clip_count} clips
          </span>
        )}
      </div>
    </div>
  );
}
