# Adding New Video Sources

## Overview
The VidSense platform uses a flexible, source-specific metadata extraction system that automatically handles different video platforms (Instagram, YouTube, TikTok, Twitter, Facebook, etc.).

## Architecture

```
Video URL → yt-dlp → raw metadata → MetadataExtractor → normalized data → Database
```

### Key Components

1. **MetadataExtractor** (`metadata_extractors.py`)
   - Main entry point that auto-detects the source
   - Routes to appropriate platform-specific extractor
   - Returns normalized data structure

2. **Platform Extractors** (InstagramExtractor, YouTubeExtractor, etc.)
   - Extract platform-specific fields
   - Handle different metadata structures
   - Normalize data into common format

3. **BaseExtractor**
   - Provides utility methods (hashtag extraction, author fallbacks)
   - Common field extraction logic
   - Shared across all platform extractors

## How It Works

### 1. Automatic Platform Detection
The system automatically detects the platform from yt-dlp's `extractor` field:

```python
extractor = MetadataExtractor(raw_meta)
print(extractor.source)  # "instagram", "youtube", "tiktok", etc.
```

### 2. Normalized Output
All extractors return the same structure:

```python
{
    # Common fields (always present)
    "title": str | None,
    "author": str | None,
    "description": str | None,
    "duration_sec": int | None,
    "hashtags": list[str],
    "clip_count": int,
    
    # Platform-specific fields (stored as JSONB)
    "metadata_json": {
        "platform": str,
        "view_count": int | None,
        "like_count": int | None,
        "comment_count": int | None,
        # ... platform-specific fields
    }
}
```

### 3. Platform-Specific Fields

Each platform stores unique metadata:

**Instagram:**
- `uploader_id` (Instagram handle)
- `like_count`, `comment_count`, `view_count`

**YouTube:**
- `channel_id`, `channel_url`
- `categories`, `tags`
- `dislike_count`
- `is_live`, `availability`

**TikTok:**
- `music_title`, `music_author` (soundtrack info)
- `share_count` (repost count)
- `uploader_id` (TikTok username)

**Twitter/X:**
- `retweet_count`, `reply_count`
- `uploader_id` (Twitter handle)

## Adding a New Platform

### Step 1: Create Extractor Class

Add a new class in `backend/app/metadata_extractors.py`:

```python
class RedditExtractor(BaseExtractor):
    """Reddit-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # Reddit-specific metadata
        metadata_json = {
            "platform": "reddit",
            "subreddit": self.meta.get("subreddit"),
            "score": self.meta.get("like_count"),  # Reddit "upvotes"
            "num_comments": self.meta.get("comment_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "author": self.meta.get("uploader"),
            "is_nsfw": self.meta.get("age_limit") == 18,
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}
```

### Step 2: Add Detection Logic

Update the `_detect_source()` method in `MetadataExtractor`:

```python
def _detect_source(self) -> str:
    extractor = self.meta.get("extractor", "").lower()
    
    if "reddit" in extractor:
        return "reddit"
    # ... existing conditions
```

### Step 3: Route to New Extractor

Update the `extract()` method in `MetadataExtractor`:

```python
def extract(self) -> Dict[str, Any]:
    if self.source == "reddit":
        return RedditExtractor(self.meta).extract()
    # ... existing conditions
```

### Step 4: Test It

Create test data and run:

```python
reddit_meta = {
    "extractor": "reddit",
    "title": "Amazing video",
    "uploader": "u/username",
    "subreddit": "videos",
    "like_count": 5000,
    "comment_count": 234,
    # ... more fields
}

extractor = MetadataExtractor(reddit_meta)
result = extractor.extract()
print(result)
```

## Best Practices

### 1. Handle Missing Fields Gracefully
Always use `.get()` with fallbacks:
```python
"like_count": self.meta.get("like_count"),  # Returns None if missing
```

### 2. Use Base Class Methods
Leverage utility methods from `BaseExtractor`:
```python
base = self._get_base_fields()  # Common fields
quality = self._get_video_quality()  # Resolution, fps, etc.
hashtags = self._extract_hashtags(description)  # Regex extraction
```

### 3. Test with Real Data
Use yt-dlp to get actual metadata:
```bash
yt-dlp --dump-json <video_url>
```

### 4. Document Platform-Specific Fields
Add comments explaining unique fields:
```python
"music_title": self.meta.get("track"),  # TikTok soundtrack
"channel_id": self.meta.get("channel_id"),  # YouTube channel
```

## Example: Full Flow

```python
# 1. User submits video URL
POST /videos/ingest_url
{
    "link": "https://www.instagram.com/reel/..."
}

# 2. Backend downloads metadata with yt-dlp
raw_meta = get_meta(link)

# 3. MetadataExtractor processes it
extractor = MetadataExtractor(raw_meta)
# Automatically detects: source = "instagram"

# 4. Instagram-specific extractor runs
extracted = extractor.extract()

# 5. Data saved to database
video.title = extracted["title"]
video.author = extracted["author"]
video.hashtags = extracted["hashtags"]
video.metadata_json = extracted["metadata_json"]
```

## Database Schema

### Videos Table
```sql
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    title TEXT,
    author TEXT,
    description TEXT,
    duration_sec INTEGER,
    clip_count INTEGER DEFAULT 1,
    hashtags JSONB DEFAULT '[]'::jsonb,
    metadata_json JSONB DEFAULT '{}'::jsonb,
    -- ... other fields
);
```

### Querying Platform-Specific Data
```python
# Get all Instagram videos with >10k views
videos = db.query(Video).filter(
    Video.metadata_json['platform'].astext == 'instagram',
    Video.metadata_json['view_count'].astext.cast(Integer) > 10000
).all()

# Get all videos with specific hashtag
videos = db.query(Video).filter(
    Video.hashtags.contains(['#viral'])
).all()
```

## Troubleshooting

### Platform Not Detected
**Symptom:** Falls back to `GenericExtractor`
**Solution:** Check `extractor` field in yt-dlp output, add to `_detect_source()`

### Missing Fields
**Symptom:** Fields are `None` in database
**Solution:** 
1. Check yt-dlp output: `yt-dlp --dump-json <url>`
2. Verify field names in extractor class
3. Ensure field exists in yt-dlp's output

### Type Errors
**Symptom:** Pylance shows assignment errors
**Solution:** These are false positives - SQLAlchemy handles them at runtime

## Future Enhancements

- **Auto-refresh:** Periodically update view/like counts
- **Trending detection:** Flag videos with high engagement growth
- **Cross-platform analytics:** Compare performance across platforms
- **Smart categorization:** Auto-tag based on metadata patterns
