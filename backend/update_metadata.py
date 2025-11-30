"""
Re-extract metadata for existing videos that don't have it.
This updates videos that were ingested before the metadata extraction system was added.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal
from app.models import Video
from app.stream_utils import get_meta, CommandError
from app.metadata_extractors import MetadataExtractor

db = SessionLocal()

try:
    # Find videos without metadata (where title is NULL or author is NULL)
    videos = db.query(Video).filter(
        (Video.title == None) | (Video.author == None)
    ).all()
    
    print(f"🔍 Found {len(videos)} videos without metadata")
    print(f"{'='*60}\n")
    
    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] Processing: {video.url[:60]}...")
        
        try:
            # Re-fetch metadata
            raw_meta = get_meta(video.url)
            
            # Extract with source-specific extractor
            extractor = MetadataExtractor(raw_meta)
            extracted = extractor.extract()
            
            # Update video
            video.title = extracted.get("title")
            video.author = extracted.get("author")
            video.description = extracted.get("description") or video.description  # Keep existing if new is None
            video.duration_sec = extracted.get("duration_sec")
            video.hashtags = extracted.get("hashtags", [])
            video.metadata_json = extracted.get("metadata_json", {})
            
            platform = video.metadata_json.get('platform', 'unknown') if video.metadata_json else 'unknown'
            hashtag_count = len(video.hashtags) if video.hashtags else 0
            
            print(f"  ✅ Updated: title='{video.title}', author='{video.author}'")
            print(f"     Platform: {platform}, Hashtags: {hashtag_count}")
            
        except CommandError as e:
            print(f"  ⚠️  Could not fetch metadata: {e}")
            continue
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
        
        print()
    
    # Commit all changes
    db.commit()
    print(f"\n{'='*60}")
    print(f"✅ Successfully updated {len(videos)} videos with metadata!")
    print(f"{'='*60}")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

print("\n💡 Run check_db.py again to see the updated metadata!")
