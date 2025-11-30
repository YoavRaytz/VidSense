import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal, engine
from app.models import Video, Transcript
from sqlalchemy import text, inspect

print(f"🔗 Connecting to: {engine.url}\n")

db = SessionLocal()

try:
    print("📊 TABLE STRUCTURES:\n")
    
    inspector = inspect(engine)
    
    # Videos table structure
    print("🎬 VIDEOS table columns:")
    for col in inspector.get_columns('videos'):
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  - {col['name']:<20} {str(col['type']):<30} {nullable}")
    
    print("\n📝 TRANSCRIPTS table columns:")
    for col in inspector.get_columns('transcripts'):
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  - {col['name']:<20} {str(col['type']):<30} {nullable}")
    
    print("\n" + "="*60)
    print(f"\n🎬 VIDEOS: {db.query(Video).count()} total\n")
    
    for v in db.query(Video).order_by(Video.created_at.desc()).limit(10):
        clips = f"({v.clip_count} clips)" if v.clip_count and v.clip_count > 1 else ""
        title = v.title if v.title else "Untitled"
        url = v.url[:50] if v.url else "No URL"
        print(f"  ID: {v.id[:16]}...")
        print(f"    Title: {title}")
        print(f"    URL: {url}")
        print(f"    Clips: {v.clip_count or 1} {clips}")
        print(f"    Created: {v.created_at}")
        print()
    
    print("="*60)
    print(f"\n📝 TRANSCRIPTS: {db.query(Transcript).count()} total")
    with_embeddings = db.query(Transcript).filter(Transcript.embedding.isnot(None)).count()
    print(f"  With embeddings: {with_embeddings}\n")
    
    for t in db.query(Transcript).limit(10):
        # Check if embedding exists (it's a numpy array)
        has_emb = "✅" if t.embedding is not None else "❌"
        text_len = len(t.text) if t.text else 0
        text_preview = (t.text[:80] + "...") if t.text and len(t.text) > 80 else (t.text or "No text")
        
        print(f"  Video ID: {t.video_id[:16]}...")
        print(f"    Text length: {text_len} chars")
        print(f"    Preview: {text_preview}")
        print(f"    Has embedding: {has_emb}")
        print()
    
    # Check pgvector extension
    print("="*60)
    print("\n🔍 PostgreSQL Extensions:")
    result = db.execute(text("SELECT extname, extversion FROM pg_extension"))
    for row in result:
        print(f"  ✅ {row[0]} (v{row[1]})")
    
    # Sample data from one video (show the NEWEST video)
    print("\n" + "="*60)
    print("\n🔍 NEWEST VIDEO DETAILS:\n")
    sample = db.query(Video).order_by(Video.created_at.desc()).first()
    if sample:
        # Print all model columns and their values
        for col in sample.__table__.columns:
            val = getattr(sample, col.name)
            # Truncate long strings for readability
            if isinstance(val, str) and len(val) > 200:
                display = val[:200] + "..."
            else:
                display = val if val is not None else "N/A"
            print(f"{col.name}: {display}")
        
        # Get transcript
        trans = db.query(Transcript).filter(Transcript.video_id == sample.id).first()
        if trans:
            print(f"\nTranscript:")
            print(f"  Text length: {len(trans.text) if trans.text else 0} chars")
            print(f"  Has embedding: {'✅' if trans.embedding is not None else '❌'}")
            print(f"  Updated: {trans.updated_at if trans.updated_at else 'N/A'}")
            if trans.embedding is not None:
                import numpy as np
                emb_array = np.array(trans.embedding)
                print(f"  Embedding shape: {emb_array.shape}")
                print(f"  Embedding sample: [{emb_array[0]:.4f}, {emb_array[1]:.4f}, ...]")
    
except Exception as e:
    import traceback
    print(f"❌ Error: {e}")
    traceback.print_exc()
finally:
    db.close()