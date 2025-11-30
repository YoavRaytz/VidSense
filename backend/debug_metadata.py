"""
Debug: Check what metadata yt-dlp returns for a specific URL
"""
import sys
sys.path.insert(0, '/home/yoav/Desktop/projects/VidSense/backend')

from app.stream_utils import get_meta
import json

# Test with the newest video URL
url = "https://www.instagram.com/diane.marieb/reel/DNgH2EbuQTl/"

print(f"🔍 Fetching metadata for: {url}\n")
print("="*60)

try:
    meta = get_meta(url)
    
    print(f"📊 Keys returned by yt-dlp:")
    for key in sorted(meta.keys()):
        print(f"  - {key}")
    
    print(f"\n{'='*60}")
    print(f"\n🔑 Key fields:")
    print(f"  extractor: {meta.get('extractor')}")
    print(f"  title: {meta.get('title')}")
    print(f"  uploader: {meta.get('uploader')}")
    print(f"  creator: {meta.get('creator')}")
    print(f"  uploader_id: {meta.get('uploader_id')}")
    print(f"  description: {meta.get('description', '')[:100]}...")
    print(f"  duration: {meta.get('duration')}")
    print(f"  view_count: {meta.get('view_count')}")
    print(f"  like_count: {meta.get('like_count')}")
    print(f"  comment_count: {meta.get('comment_count')}")
    
    print(f"\n{'='*60}")
    print(f"\n📄 Full metadata (JSON):")
    print(json.dumps(meta, indent=2, default=str))
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
