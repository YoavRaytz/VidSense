import os
from celery import Celery
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Video, Transcript
from transcribe.gemini_client import GeminiTranscriber

# Celery app
celery_app = Celery(
    'transcription',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

@celery_app.task(name='transcribe_video')
def transcribe_video_task(video_id: str):
    """Transcribe video using Gemini API"""
    db: Session = SessionLocal()
    
    try:
        video = db.get(Video, video_id)
        if not video:
            print(f"Video {video_id} not found")
            return
        
        print(f"Transcribing video: {video_id}")
        
        # Initialize Gemini client
        gemini = GeminiTranscriber(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Transcribe video
        transcript_text = gemini.transcribe_video_url(video.url)
        
        # Save transcript
        transcript = Transcript(
            video_id=video_id,
            text=transcript_text
        )
        db.add(transcript)
        db.commit()
        
        print(f"✅ Transcription complete for video {video_id}")
        
        # Enqueue embedding generation
        from celery import current_app
        current_app.send_task('generate_embeddings', args=[video_id])
        
    except Exception as e:
        print(f"❌ Transcription failed for video {video_id}: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    celery_app.worker_main()
