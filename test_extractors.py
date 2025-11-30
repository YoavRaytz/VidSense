"""
Test the metadata extractors with sample data from different sources.
Run this to see how metadata extraction works for different platforms.
"""
from backend.app.metadata_extractors import MetadataExtractor
import json


# Sample Instagram metadata (simplified from real yt-dlp output)
instagram_meta = {
    "extractor": "Instagram",
    "title": "Amazing sunset timelapse",
    "description": "Check out this beautiful sunset! #sunset #nature #photography",
    "uploader": "john_doe",
    "uploader_id": "johndoe123",
    "duration": 45,
    "view_count": 15234,
    "like_count": 892,
    "comment_count": 45,
    "upload_date": "20241101",
    "thumbnail": "https://example.com/thumb.jpg",
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "clip_count": 1,
}

# Sample YouTube metadata
youtube_meta = {
    "extractor": "youtube",
    "title": "How to Build a Web App - Tutorial",
    "description": "Learn web development from scratch! #coding #tutorial #webdev",
    "uploader": "TechChannel",
    "channel_id": "UCxxx",
    "channel_url": "https://youtube.com/@techchannel",
    "duration": 1205,
    "view_count": 125000,
    "like_count": 3400,
    "dislike_count": 45,
    "comment_count": 567,
    "upload_date": "20241025",
    "thumbnail": "https://example.com/yt_thumb.jpg",
    "categories": ["Education", "Technology"],
    "tags": ["coding", "tutorial", "python", "javascript"],
    "width": 1920,
    "height": 1080,
    "fps": 60,
    "clip_count": 1,
}

# Sample TikTok metadata
tiktok_meta = {
    "extractor": "TikTok",
    "title": "Dance challenge 💃",
    "description": "Join the trend! #dance #viral #fyp #trending",
    "uploader": "dancer_girl",
    "uploader_id": "dancergirl22",
    "duration": 15,
    "view_count": 2500000,
    "like_count": 150000,
    "comment_count": 3400,
    "repost_count": 8900,
    "upload_date": "20241102",
    "thumbnail": "https://example.com/tt_thumb.jpg",
    "track": "Popular Song 2024",
    "artist": "Artist Name",
    "width": 720,
    "height": 1280,
    "fps": 30,
    "clip_count": 1,
}


def test_extractor(name: str, meta: dict):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    extractor = MetadataExtractor(meta)
    extracted = extractor.extract()
    
    print(f"\nDetected Source: {extractor.source}")
    print(f"\nExtracted Fields:")
    print(f"  Title: {extracted.get('title')}")
    print(f"  Author: {extracted.get('author')}")
    print(f"  Duration: {extracted.get('duration_sec')}s")
    print(f"  Hashtags: {extracted.get('hashtags')}")
    print(f"  Clip Count: {extracted.get('clip_count')}")
    
    print(f"\nMetadata JSON:")
    print(json.dumps(extracted.get('metadata_json', {}), indent=2))


if __name__ == "__main__":
    print("🧪 Testing Source-Specific Metadata Extractors")
    print("This demonstrates how different platforms are handled\n")
    
    test_extractor("Instagram Reel", instagram_meta)
    test_extractor("YouTube Video", youtube_meta)
    test_extractor("TikTok Video", tiktok_meta)
    
    print("\n" + "="*60)
    print("✅ All extractors tested!")
    print("="*60)
    print("\n💡 Key Benefits:")
    print("  • Automatic platform detection")
    print("  • Platform-specific fields (e.g., TikTok music, YT channel)")
    print("  • Consistent output format across all sources")
    print("  • Easy to add new platforms (just create new extractor class)")
