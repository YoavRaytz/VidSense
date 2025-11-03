# backend/app/stream_utils.py
import os, shlex, subprocess, uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple  # <-- Add this line
import json

YTDLP_BIN = os.getenv("YTDLP_BIN", "yt-dlp")
YTDLP_COOKIES = os.getenv("YTDLP_COOKIES")
GST_BIN = os.getenv("GST_BIN", "gst-launch-1.0")
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
TMP_DIR = Path(os.getenv("TMP_DIR", "/tmp/app-videos"))
TMP_DIR.mkdir(parents=True, exist_ok=True)

class CommandError(RuntimeError):
    pass

def _gst_cmd_for(url: str, out_path: Path) -> str:
    # exact pipeline you use in your shell
    return (
        f'{shlex.quote(GST_BIN)} -e '
        f'souphttpsrc location="{url}" is-live=false keep-alive=true '
        f'! queue2 use-buffering=true ! typefind ! qtdemux name=demux '
        f'mp4mux name=mux faststart=true '
        f'demux.video_0 ! queue ! h264parse ! queue ! mux.video_0 '
        f'demux.audio_0 ! queue ! aacparse ! queue ! mux.audio_0 '
        f'mux. ! filesink location="{out_path}"'
    )

def remux_to_temp_mp4(stream_url: str, timeout: int = 300) -> Path:
    out_path = TMP_DIR / f"{uuid.uuid4().hex}.mp4"

    # ---------- Try FFmpeg (robust) ----------
    ff_cmd = [
        FFMPEG_BIN,
        "-y", "-nostdin", "-loglevel", "error",
        "-i", stream_url,
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ]
    print("[remux] URL:", stream_url[:140], "...")
    print("[remux] FFmpeg:", " ".join(shlex.quote(x) for x in ff_cmd))
    try:
        subprocess.check_output(ff_cmd, stderr=subprocess.STDOUT, timeout=timeout)
        if out_path.exists() and out_path.stat().st_size > 1024:
            return out_path
        else:
            try: out_path.unlink(missing_ok=True)
            except Exception: pass
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        tail = ""
        if hasattr(e, "output") and isinstance(e.output, (bytes, bytearray)):
            tail = e.output[-800:].decode(errors="ignore")
        print("[remux] FFmpeg failed, falling back to GStreamer. Tail:\n", tail)

    # ---------- Fallback: GStreamer (your exact pipeline) ----------
    gst_cmd = _gst_cmd_for(stream_url, out_path)
    print("[remux] GST:", gst_cmd)
    env = os.environ.copy()
    env.setdefault("GST_DEBUG", "2")  # bump to 3/4 to see more
    try:
        subprocess.check_output(gst_cmd, shell=True, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    except subprocess.CalledProcessError as e:
        tail = e.output.decode(errors="ignore")[-800:] if isinstance(e.output, (bytes, bytearray)) else str(e)
        raise CommandError(f"GStreamer remux failed:\n{tail}")
    except subprocess.TimeoutExpired:
        raise CommandError("GStreamer remux timed out")

    if not out_path.exists() or out_path.stat().st_size < 1024:
        try: out_path.unlink(missing_ok=True)
        except Exception: pass
        raise CommandError("Remux output missing or too small (0 bytes)")
    return out_path



def _cookies_args() -> list[str]:
    if not YTDLP_COOKIES:
        return []
    return ["--cookies", YTDLP_COOKIES] if YTDLP_COOKIES.endswith(".txt") else ["--cookies-from-browser", YTDLP_COOKIES]

def get_meta(link: str, timeout: int = 25) -> Dict[str, Any]:
    """Return yt-dlp JSON for a link. Works for single or multi-video posts."""
    cmd = [YTDLP_BIN, *_cookies_args(), "-J", link]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, text=True)
    except subprocess.CalledProcessError as e:
        raise CommandError(f"yt-dlp -J failed: {e.output[-500:]}")
    data = json.loads(out)
    
    # normalize: count clips and caption/description
    if "entries" in data and isinstance(data["entries"], list):
        clip_count = sum(1 for e in data["entries"] if e and (e.get("url") or e.get("formats")))
        # For multi-video posts, use first entry's metadata
        first_entry = next((e for e in data["entries"] if e), {})
        metadata_source = {**data, **first_entry}  # Merge with preference for entry data
    else:
        clip_count = 1
        metadata_source = data
    
    description = (metadata_source.get("description") or metadata_source.get("fulltitle") or "").strip()
    
    # Extract all useful metadata fields (return full data structure)
    return {
        "raw": data,
        "clip_count": max(1, clip_count),
        "description": description,
        # Platform/source
        "extractor": metadata_source.get("extractor"),
        "extractor_key": metadata_source.get("extractor_key"),
        # Basic info
        "title": metadata_source.get("title") or metadata_source.get("fulltitle"),
        "uploader": metadata_source.get("uploader"),
        "uploader_id": metadata_source.get("uploader_id"),
        "uploader_url": metadata_source.get("uploader_url"),
        "creator": metadata_source.get("creator"),
        "channel": metadata_source.get("channel"),
        "channel_id": metadata_source.get("channel_id"),
        "channel_url": metadata_source.get("channel_url"),
        # Video properties
        "duration": metadata_source.get("duration"),
        "width": metadata_source.get("width"),
        "height": metadata_source.get("height"),
        "fps": metadata_source.get("fps"),
        "resolution": metadata_source.get("resolution"),
        "format": metadata_source.get("format"),
        # Engagement metrics
        "view_count": metadata_source.get("view_count"),
        "like_count": metadata_source.get("like_count"),
        "dislike_count": metadata_source.get("dislike_count"),
        "comment_count": metadata_source.get("comment_count"),
        "repost_count": metadata_source.get("repost_count"),
        # Additional metadata
        "upload_date": metadata_source.get("upload_date"),
        "timestamp": metadata_source.get("timestamp"),
        "thumbnail": metadata_source.get("thumbnail"),
        "categories": metadata_source.get("categories", []),
        "tags": metadata_source.get("tags", []),
        "is_live": metadata_source.get("is_live"),
        "availability": metadata_source.get("availability"),
        "age_limit": metadata_source.get("age_limit"),
        # Platform-specific (TikTok)
        "track": metadata_source.get("track"),
        "artist": metadata_source.get("artist"),
    }

def get_fresh_stream_url(link: str, clip_index: Optional[int] = None, timeout: int = 20) -> str:
    """
    Return a short-lived direct MP4 URL. If clip_index is provided (1-based),
    use --playlist-items to target that clip in a sidecar.
    Works for Instagram and Facebook (requires cookies for some private/age-gated content).
    """
    cookies_arg = _cookies_args()
    # Prefer mp4 with audio+video; fall back to best available
    base = [YTDLP_BIN, *cookies_arg, "-f", "best[ext=mp4][acodec!=none][vcodec!=none]/best"]
    if clip_index:
        base += ["--playlist-items", str(clip_index)]
    cmd = [*base, "-g", link]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, text=True)
    except subprocess.CalledProcessError as e:
        raise CommandError(f"yt-dlp failed: {e.output[-500:]}")
    url = (out or "").strip().splitlines()[0] if out else ""
    if not url:
        raise CommandError("No URL returned by yt-dlp")
    return url

def download_video(link: str, clip_index: Optional[int] = None, timeout_probe: int = 25, timeout_remux: int = 300) -> Path:
    """
    Convenience helper: resolve a direct stream URL then remux to local MP4.
    """
    # Optional: quick probe to fail early if totally unsupported
    try:
        _ = get_meta(link, timeout=timeout_probe)
    except Exception as e:
        # Not fatal in all cases, but helpful to surface auth/login issues early
        print(f"[download_video] probe warning: {e}")
    direct = get_fresh_stream_url(link, clip_index=clip_index, timeout=timeout_probe)
    return remux_to_temp_mp4(direct, timeout=timeout_remux)

def safe_unlink(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass

# --- Optional back-compat: minimal image downloader (for legacy imports) ---

def download_image(image_url: str, output_path: Optional[Path] = None) -> Path:
    """
    Minimal shim kept only so older code importing `download_image` doesn't break.
    We don't do any image processing; just download bytes to a .jpg on disk.
    """
    if not output_path:
        output_path = TMP_DIR / f"{uuid.uuid4().hex}.jpg"
    try:
        # Local import to avoid hard dependency if never used
        import requests  # type: ignore
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        with requests.get(image_url, headers=headers, timeout=30, stream=True) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return output_path
    except Exception as e:
        raise CommandError(f"Image download failed: {type(e).__name__}: {e}")
