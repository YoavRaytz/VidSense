"""
Source-specific metadata extraction for different video platforms.
Each platform has different metadata structure from yt-dlp.
"""
from typing import Dict, Any, List, Optional
import re


class MetadataExtractor:
    """Base class for extracting metadata from yt-dlp results."""
    
    def __init__(self, meta: Dict[str, Any]):
        self.meta = meta
        self.source = self._detect_source()
    
    def _detect_source(self) -> str:
        """Detect the source platform from metadata."""
        extractor = self.meta.get("extractor", "").lower()
        
        if "instagram" in extractor:
            return "instagram"
        elif "youtube" in extractor or "yt" in extractor:
            return "youtube"
        elif "tiktok" in extractor:
            return "tiktok"
        elif "twitter" in extractor or "x.com" in extractor:
            return "twitter"
        elif "facebook" in extractor:
            return "facebook"
        else:
            return "web"  # generic fallback
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract normalized metadata based on source.
        Returns a dict with standard fields that can be mapped to the Video model.
        """
        # Route to source-specific extractor
        if self.source == "instagram":
            return InstagramExtractor(self.meta).extract()
        elif self.source == "youtube":
            return YouTubeExtractor(self.meta).extract()
        elif self.source == "tiktok":
            return TikTokExtractor(self.meta).extract()
        elif self.source == "twitter":
            return TwitterExtractor(self.meta).extract()
        elif self.source == "facebook":
            return FacebookExtractor(self.meta).extract()
        else:
            return GenericExtractor(self.meta).extract()


class BaseExtractor:
    """Base extractor with common utility methods."""
    
    def __init__(self, meta: Dict[str, Any]):
        self.meta = meta
    
    def _extract_hashtags(self, text: Optional[str]) -> List[str]:
        """Extract hashtags from text using regex."""
        if not text:
            return []
        return re.findall(r'#\w+', text)
    
    def _get_author(self) -> Optional[str]:
        """Extract author/creator name with fallbacks."""
        return (
            self.meta.get("uploader") or 
            self.meta.get("creator") or 
            self.meta.get("channel") or
            self.meta.get("uploader_id") or
            None
        )
    
    def _get_base_fields(self) -> Dict[str, Any]:
        """Extract common fields present across all platforms."""
        description = self.meta.get("description") or None
        
        return {
            "title": self.meta.get("title") or None,
            "author": self._get_author(),
            "description": description,
            "duration_sec": self.meta.get("duration"),
            "hashtags": self._extract_hashtags(description),
            "clip_count": int(self.meta.get("clip_count") or 1),
        }
    
    def _get_video_quality(self) -> Dict[str, Any]:
        """Extract video quality metadata."""
        return {
            "width": self.meta.get("width"),
            "height": self.meta.get("height"),
            "fps": self.meta.get("fps"),
            "format": self.meta.get("format"),
            "resolution": self.meta.get("resolution"),
        }


class InstagramExtractor(BaseExtractor):
    """Instagram-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # Instagram-specific metadata
        metadata_json = {
            "platform": "instagram",
            "like_count": self.meta.get("like_count"),
            "comment_count": self.meta.get("comment_count"),
            "view_count": self.meta.get("view_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "uploader_id": self.meta.get("uploader_id"),  # Instagram handle
            "uploader_url": self.meta.get("uploader_url"),
            "channel_url": self.meta.get("channel_url"),
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}


class YouTubeExtractor(BaseExtractor):
    """YouTube-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # YouTube-specific metadata
        metadata_json = {
            "platform": "youtube",
            "view_count": self.meta.get("view_count"),
            "like_count": self.meta.get("like_count"),
            "dislike_count": self.meta.get("dislike_count"),
            "comment_count": self.meta.get("comment_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "channel_id": self.meta.get("channel_id"),
            "channel_url": self.meta.get("channel_url"),
            "categories": self.meta.get("categories", []),
            "tags": self.meta.get("tags", []),
            "is_live": self.meta.get("is_live"),
            "availability": self.meta.get("availability"),
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}


class TikTokExtractor(BaseExtractor):
    """TikTok-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # TikTok-specific metadata
        metadata_json = {
            "platform": "tiktok",
            "view_count": self.meta.get("view_count"),
            "like_count": self.meta.get("like_count"),
            "comment_count": self.meta.get("comment_count"),
            "share_count": self.meta.get("repost_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "uploader_id": self.meta.get("uploader_id"),  # TikTok username
            "uploader_url": self.meta.get("uploader_url"),
            "channel_url": self.meta.get("channel_url"),
            "music_title": self.meta.get("track"),
            "music_author": self.meta.get("artist"),
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}


class TwitterExtractor(BaseExtractor):
    """Twitter/X-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # Twitter-specific metadata
        metadata_json = {
            "platform": "twitter",
            "view_count": self.meta.get("view_count"),
            "like_count": self.meta.get("like_count"),
            "retweet_count": self.meta.get("repost_count"),
            "reply_count": self.meta.get("comment_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "uploader_id": self.meta.get("uploader_id"),  # Twitter handle
            "uploader_url": self.meta.get("uploader_url"),
            "channel_url": self.meta.get("channel_url"),
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}


class FacebookExtractor(BaseExtractor):
    """Facebook-specific metadata extraction."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # Construct Facebook profile URL from uploader_id if available
        uploader_url = self.meta.get("uploader_url")
        uploader_id = self.meta.get("uploader_id")
        if not uploader_url and uploader_id:
            # Facebook profile URL format: https://www.facebook.com/profile.php?id=USER_ID
            uploader_url = f"https://www.facebook.com/profile.php?id={uploader_id}"
        
        # Try to scrape engagement stats (likes, comments, shares) from Facebook page
        # This is optional and may fail due to Facebook anti-bot measures
        engagement = {}
        try:
            from .stream_utils import scrape_facebook_engagement
            video_url = self.meta.get("webpage_url") or self.meta.get("original_url")
            if video_url:
                engagement = scrape_facebook_engagement(video_url)
                print(f"[FacebookExtractor] Scraped engagement: {engagement}")
        except Exception as e:
            print(f"[FacebookExtractor] Could not scrape engagement: {e}")
        
        # Facebook-specific metadata
        # Prefer scraped values (if not None), fall back to yt-dlp values (usually null)
        # Use 'if is not None' to preserve distinction between 0 and None
        scraped_likes = engagement.get("like_count")
        scraped_comments = engagement.get("comment_count")
        scraped_shares = engagement.get("share_count")
        
        metadata_json = {
            "platform": "facebook",
            "view_count": self.meta.get("view_count"),
            "like_count": scraped_likes if scraped_likes is not None else self.meta.get("like_count"),
            "comment_count": scraped_comments if scraped_comments is not None else self.meta.get("comment_count"),
            "share_count": scraped_shares if scraped_shares is not None else self.meta.get("repost_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            "uploader_url": uploader_url,
            "channel_url": self.meta.get("channel_url") or uploader_url,
            "uploader_id": uploader_id,
            **self._get_video_quality(),
        }
        
        return {**base, "metadata_json": metadata_json}


class GenericExtractor(BaseExtractor):
    """Fallback extractor for unknown sources."""
    
    def extract(self) -> Dict[str, Any]:
        base = self._get_base_fields()
        
        # Generic metadata - capture everything we can
        metadata_json = {
            "platform": self.meta.get("extractor", "web"),
            "view_count": self.meta.get("view_count"),
            "like_count": self.meta.get("like_count"),
            "comment_count": self.meta.get("comment_count"),
            "upload_date": self.meta.get("upload_date"),
            "thumbnail": self.meta.get("thumbnail"),
            **self._get_video_quality(),
            # Store any extra fields we might have missed
            "raw_extractor": self.meta.get("extractor"),
        }
        
        return {**base, "metadata_json": metadata_json}
