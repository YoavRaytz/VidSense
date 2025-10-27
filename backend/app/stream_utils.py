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
    else:
        clip_count = 1
    description = (data.get("description") or data.get("fulltitle") or "").strip()
    return {"raw": data, "clip_count": max(1, clip_count), "description": description}

def get_fresh_stream_url(link: str, clip_index: Optional[int] = None, timeout: int = 20) -> str:
    """
    Return a short-lived direct MP4 URL. If clip_index is provided (1-based),
    use --playlist-items to target that clip in a sidecar.
    """
    cookies_arg = _cookies_args()
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



def safe_unlink(p: Path) -> None:
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass
