from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
from .db import get_db
from .models import Video
from .stream_utils import get_fresh_stream_url, remux_to_temp_mp4

app = FastAPI(title="VidSense Streaming Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/videos/{video_id}/stream")
def stream_video(video_id: str, clip: Optional[int] = None, db: Session = Depends(get_db)):
    """Get fresh stream URL for video"""
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Get fresh stream URL (video.url is a string property)
    try:
        url_str = str(video.url)  # Explicitly convert Column to string
        stream_url = get_fresh_stream_url(url_str, clip)
        return {"url": stream_url}
    except Exception as e:
        raise HTTPException(502, f"Could not obtain stream URL: {e}")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "streaming"}
