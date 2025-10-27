# backend/migrate_embeddings.py
"""
Migration script to generate embeddings for existing transcripts.
Run this once to populate embeddings for videos that were created before the embedding feature.
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.models import Video, Transcript
from app.embeddings import embed_text, combine_text_for_embedding

def migrate_embeddings():
    """Generate embeddings for all transcripts that don't have them."""
    db = SessionLocal()
    
    try:
        # Find all transcripts without embeddings
        transcripts = db.query(Transcript).filter(Transcript.embedding == None).all()
        
        if not transcripts:
            print("✅ All transcripts already have embeddings!")
            return
        
        print(f"📊 Found {len(transcripts)} transcripts without embeddings")
        print("🔄 Generating embeddings...\n")
        
        for idx, transcript in enumerate(transcripts, 1):
            try:
                # Get associated video for caption/description
                video = db.get(Video, transcript.video_id)
                if not video:
                    print(f"⚠️  [{idx}/{len(transcripts)}] Video not found for transcript {transcript.video_id}, skipping")
                    continue
                
                # Get text content
                text_val = getattr(transcript, 'text', None)
                if text_val is None:
                    print(f"⚠️  [{idx}/{len(transcripts)}] No text for transcript {transcript.video_id}, skipping")
                    continue
                
                transcript_text = str(text_val)
                
                # Get description
                desc_val = getattr(video, 'description', None)
                desc_str = str(desc_val) if desc_val is not None else None
                
                # Combine and embed
                combined_text = combine_text_for_embedding(transcript_text, desc_str)
                embedding = embed_text(combined_text)
                
                # Update transcript
                setattr(transcript, 'embedding', embedding)
                
                # Get video title for display
                title_val = getattr(video, 'title', None)
                title = str(title_val) if title_val else 'Untitled'
                
                print(f"✅ [{idx}/{len(transcripts)}] {title[:50]}")
                
                # Commit every 10 records to avoid memory issues
                if idx % 10 == 0:
                    db.commit()
                    print(f"   💾 Committed batch (total: {idx})\n")
                
            except Exception as e:
                print(f"❌ [{idx}/{len(transcripts)}] Error processing {transcript.video_id}: {e}")
                continue
        
        # Final commit
        db.commit()
        print(f"\n✅ Done! Generated embeddings for {len(transcripts)} transcripts")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting embedding migration...")
    print("⏳ This may take a few minutes for large databases...\n")
    migrate_embeddings()
