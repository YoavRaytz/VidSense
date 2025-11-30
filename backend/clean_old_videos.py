"""
Delete all old videos (keep only the newest N videos)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal
from app.models import Video, Transcript

db = SessionLocal()

try:
    # How many videos to keep?
    KEEP_NEWEST = 0  # Set to 0 to delete ALL videos
    
    # Get all videos ordered by date
    all_videos = db.query(Video).order_by(Video.created_at.desc()).all()
    
    print(f"📊 Total videos in database: {len(all_videos)}")
    
    if KEEP_NEWEST > 0:
        videos_to_delete = all_videos[KEEP_NEWEST:]
        print(f"✅ Keeping newest {KEEP_NEWEST} videos")
    else:
        videos_to_delete = all_videos
        print(f"⚠️  Deleting ALL videos!")
    
    print(f"🗑️  Videos to delete: {len(videos_to_delete)}\n")
    
    if not videos_to_delete:
        print("✅ No videos to delete!")
        sys.exit(0)
    
    # Confirm
    print("Videos to be deleted:")
    for v in videos_to_delete[:5]:  # Show first 5
        title = v.title if v.title else "Untitled"
        print(f"  - {title[:50]} ({v.created_at})")
    if len(videos_to_delete) > 5:
        print(f"  ... and {len(videos_to_delete) - 5} more")
    
    print(f"\n{'='*60}")
    response = input("⚠️  Are you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled")
        sys.exit(0)
    
    # Delete videos and their transcripts
    deleted_count = 0
    for video in videos_to_delete:
        # Delete transcript if exists
        transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
        if transcript:
            db.delete(transcript)
        
        # Delete video
        db.delete(video)
        deleted_count += 1
        
        if deleted_count % 10 == 0:
            print(f"  Deleted {deleted_count}/{len(videos_to_delete)}...")
    
    db.commit()
    
    print(f"\n✅ Successfully deleted {deleted_count} videos!")
    print(f"📊 Remaining videos: {db.query(Video).count()}")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
