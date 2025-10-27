import { useRef, useEffect } from 'react';

interface VideoPlayerProps {
  videoId: string;
  streamUrl: string | null;
  clipCount: number;
  clip: number;
  onClipChange: (clip: number) => void;
  disabled?: boolean;
}

export default function VideoPlayer({ 
  videoId, 
  streamUrl, 
  clipCount, 
  clip, 
  onClipChange, 
  disabled = false 
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Restart playback when stream URL changes
  useEffect(() => {
    if (streamUrl && videoRef.current) {
      videoRef.current.load();
    }
  }, [streamUrl]);

  if (!streamUrl) {
    return null;
  }

  return (
    <>
      {/* Clip navigation buttons (only for multi-clip posts) */}
      {clipCount > 1 && (
        <div className="row" style={{ marginBottom: 10, alignItems: 'center', gap: 8 }}>
          <button 
            className="btn" 
            onClick={() => onClipChange(Math.max(1, clip - 1))} 
            disabled={clip <= 1 || disabled}
          >
            « Prev
          </button>
          <div className="muted">Clip {clip} / {clipCount}</div>
          <button 
            className="btn" 
            onClick={() => onClipChange(Math.min(clipCount, clip + 1))} 
            disabled={clip >= clipCount || disabled}
          >
            Next »
          </button>
        </div>
      )}
      <video ref={videoRef} src={streamUrl} controls className="video" />
    </>
  );
}
