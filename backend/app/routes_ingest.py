from __future__ import annotations

import os
from pathlib import Path
import pprint
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query


from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import get_db
from .models import Video, Transcript
from .schemas import TranscriptOut, TranscriptUpdate
from .stream_utils import (
    get_fresh_stream_url,
    remux_to_temp_mp4,
    safe_unlink,
    CommandError,
    get_meta
)

from .transcribe.gemini_client import GeminiTranscriber
import os, json, traceback  # <-- add traceback here


router = APIRouter(prefix="/videos", tags=["videos"])


# ---------- utils ----------

def _log(msg: str):
    # simple print wrapper that flushes (so you see logs in real time)
    print(msg, flush=True)


# ---------- payloads ----------

class IngestURL(BaseModel):
    link: str
    source: str | None = "web"


# ---------- routes ----------

@router.post("/ingest_url")
def ingest_url(payload: IngestURL, db: Session = Depends(get_db)):
    vid = uuid4().hex
    v = Video(
        id=vid,
        source=payload.source or "web",
        url=payload.link,
        title=None,
    )
    db.add(v)
    try:
        db.flush()
        # pull metadata (caption + clip count)
        try:
            meta = get_meta(payload.link)
            v.description = meta.get("description") or None
            v.clip_count = int(meta.get("clip_count") or 1)
        except CommandError as e:
            # non-fatal: still allow ingest
            print(f"[ingest_url][meta warn] {e}")
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"DB error: {e}")

    return {"video_id": v.id, "clip_count": v.clip_count, "description": v.description}


@router.get("/{video_id}/meta")
def get_video_meta(video_id: str, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    return {"video_id": v.id, "description": v.description, "clip_count": v.clip_count}


@router.get("/{video_id}/stream")
def get_stream_url_route(
    video_id: str,
    clip: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db)
):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    try:
        url = get_fresh_stream_url(v.url, clip_index=clip)
    except CommandError as e:
        raise HTTPException(502, f"Could not obtain stream URL: {e}")
    return {"url": url}



@router.get("/{video_id}/stream")
def get_stream_url(video_id: str, db: Session = Depends(get_db)):
    """
    Return a short-lived direct MP4 URL for the stored link.
    """
    _log(f"[stream] video_id={video_id}")

    v = db.get(Video, video_id)
    if not v:
        _log(f"[stream] 404 video not found")
        raise HTTPException(404, "Video not found")

    try:
        url = get_fresh_stream_url(v.url)
        _log(f"[stream] ok url={url[:120]}...")
        return {"url": url}
    except CommandError as e:
        _log(f"[stream][ERROR] {e}")
        raise HTTPException(502, f"Could not obtain stream URL: {e}")


@router.post("/{video_id}:generate_transcript", response_model=TranscriptOut)
def generate_transcript(
    video_id: str,
    clip: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db)
):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")

    print(f"[transcribe] start video_id={video_id} clip={clip or 1}")

    # ✅ Fail fast if key isn’t set (avoids generic 500)
    if not os.getenv("GEMINI_API_KEY"):
        print("[transcribe][FATAL] GEMINI_API_KEY not set")
        raise HTTPException(500, "GEMINI_API_KEY not set")

    temp = None
    try:
        stream_url = get_fresh_stream_url(v.url, clip_index=clip)
        print(f"[transcribe] stream URL len={len(stream_url)}")

        temp = remux_to_temp_mp4(stream_url)
        size = os.path.getsize(temp)
        print(f"[transcribe] remux ok: path={temp} size={size} bytes")
        if size < 2048:
            safe_unlink(temp)
            raise HTTPException(502, "Remux produced too small file (<2KB)")

        transcriber = GeminiTranscriber()
        print("[transcribe] calling Gemini…")
        result = transcriber.transcribe(str(temp))
        print(f"[transcribe] gemini ok; keys={list(result.keys())}")

    except HTTPException:
        raise
    except CommandError as e:
        traceback.print_exc()
        raise HTTPException(502, f"Fetch/remux error: {e}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(502, f"Transcription error: {e}")
    finally:
        if temp:
            safe_unlink(temp)
            print("[transcribe] temp file cleaned")

    # store text (append per-clip)
    text = (result.get("transcript") or "").strip()
    if not text:
        raw = result.get("raw")
        if isinstance(raw, (dict, list)):
            text = json.dumps(raw, ensure_ascii=False)
        elif isinstance(raw, str):
            text = raw
        else:
            text = json.dumps(result, ensure_ascii=False)

    # Only add clip header if there are multiple clips
    header = ""
    if v.clip_count > 1:
        clip_label = f"[Clip {clip or 1}]"
        header = f"\n\n--- {clip_label} ---\n"

    t = db.get(Transcript, video_id)
    if t:
        t.text = (t.text or "") + header + text
    else:
        t = Transcript(video_id=video_id, text=(header + text).lstrip())
        db.add(t)
    db.commit()

    return TranscriptOut(video_id=video_id, title=v.title, url=v.url, media_path=v.media_path, text=t.text)



@router.get("/{video_id}/transcript", response_model=TranscriptOut)
def get_transcript(video_id: str, db: Session = Depends(get_db)):
    _log(f"[get_transcript] video_id={video_id}")

    v = db.get(Video, video_id)
    if not v:
        _log("[get_transcript] 404 video not found")
        raise HTTPException(404, "Video not found")

    t = db.get(Transcript, video_id)
    if not t:
        _log("[get_transcript] 404 transcript not found")
        raise HTTPException(404, "Transcript not found")

    _log(f"[get_transcript] ok chars={len(t.text or '')}")
    return TranscriptOut(
        video_id=video_id,
        title=v.title,
        url=v.url,
        media_path=v.media_path,
        text=t.text,
    )


@router.put("/{video_id}/transcript")
def put_transcript(video_id: str, payload: TranscriptUpdate, db: Session = Depends(get_db)):
    _log(f"[put_transcript] video_id={video_id} chars={len(payload.text or '')}")

    v = db.get(Video, video_id)
    if not v:
        _log("[put_transcript] 404 video not found")
        raise HTTPException(404, "Video not found")

    try:
        t = db.get(Transcript, video_id)
        if t is None:
            t = Transcript(video_id=video_id, text=payload.text or "")
            db.add(t)
            _log("[put_transcript] creating new transcript row")
        else:
            t.text = payload.text or ""
            _log("[put_transcript] updating transcript row")

        db.flush()
        db.commit()
        _log("[put_transcript] ok")
        return {"ok": True}

    except SQLAlchemyError as e:
        db.rollback()
        _log(f"[put_transcript][DB ERROR] {e.__class__.__name__}: {e}")
        raise HTTPException(500, f"DB error saving transcript: {e.__class__.__name__}: {e}")


# ---------- tiny health checks (optional but handy) ----------

@router.get("/__health/genai")
def health_genai():
    try:
        from google import genai  # noqa
        key_ok = bool(os.getenv("GEMINI_API_KEY"))
        return {"ok": True, "gemini_key_present": key_ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/__health/stream")
def health_stream(sample_link: Optional[str] = None):
    """Quickly test yt-dlp URL resolver. Pass ?sample_link=... to try."""
    link = sample_link or "https://www.instagram.com/reel/DL6hKXqR61T/"
    try:
        url = get_fresh_stream_url(link)
        return {"ok": True, "url_prefix": url[:100]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
