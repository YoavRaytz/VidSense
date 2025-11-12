import os
from celery import Celery
from sqlalchemy.orm import Session
from db import SessionLocal
from models import Video, Transcript
from embeddings import embed_text, combine_text_for_embedding

# Celery app
celery_app = Celery(
    'embedding',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)

@celery_app.task(name='generate_embeddings')
def generate_embeddings_task(video_id: str):
    """Generate embeddings for video transcript"""
    db: Session = SessionLocal()
    
    try:
        video = db.get(Video, video_id)
        if not video:
            print(f"Video {video_id} not found")
            return
        
        print(f"Generating embeddings for video: {video_id}")
        
        # Get transcript
        transcript = db.get(Transcript, video_id)
        
        if not transcript or not transcript.text:
            print(f"No transcript found for video {video_id}")
            return
        
        # Generate embedding for transcript + description
        desc_str = video.description or ""
        combined_text = combine_text_for_embedding(transcript.text, desc_str)
        embedding = embed_text(combined_text)
        
        # Update transcript with embedding
        transcript.embedding = embedding
        
        db.commit()
        
        print(f"✅ Generated embedding for video {video_id}")
        
    except Exception as e:
        print(f"❌ Embedding generation failed for video {video_id}: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    celery_app.worker_main()
