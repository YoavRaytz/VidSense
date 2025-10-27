from __future__ import annotations

import os
from pathlib import Path
import pprint
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
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
)
from .transcribe.gemini_client import GeminiTranscriber


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
    """
    Register a video row. Since the 'videos.id' column doesn't autogenerate,
    we assign a UUID ourselves.
    """
    _log(f"[ingest_url] link={payload.link} source={payload.source or 'web'}")

    try:
        v = Video(
            id=uuid4().hex,                 # <-- explicit PK (string)
            source=payload.source or "web",
            url=payload.link,
            title=None,
        )
        db.add(v)
        db.flush()
        db.commit()
        _log(f"[ingest_url] new video_id={v.id}")
        return {"video_id": v.id}

    except SQLAlchemyError as e:
        db.rollback()
        _log(f"[ingest_url][DB ERROR] {e.__class__.__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"DB error inserting video: {e.__class__.__name__}: {e}",
        )


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
def generate_transcript(video_id: str, db: Session = Depends(get_db)):
    """
    Fetch fresh stream -> remux temp mp4 -> send to Gemini -> save transcript.
    """
    _log(f"[transcribe] video_id={video_id}")

    v = db.get(Video, video_id)
    if not v:
        _log("[transcribe] 404 video not found")
        raise HTTPException(404, "Video not found")

    temp_path: Optional[Path] = None
    try:
        # 1) Fresh signed/short-lived stream URL
        stream_url = get_fresh_stream_url(v.url)
        _log(f"[transcribe] stream_url={stream_url[:140]}...")

        # 2) Remux to local MP4 (FFmpeg first; GST fallback handled inside)
        temp_path = remux_to_temp_mp4(stream_url)
        _log(f"[transcribe] remux done -> {temp_path} ({temp_path.stat().st_size} bytes)")

        # 3) Transcribe with Gemini
        transcriber = GeminiTranscriber()
        result = transcriber.transcribe(str(temp_path))
        # _log(f"[transcribe] gemini result: {result}")
        pprint.pprint(f"[transcribe] gemini result: {result}")
        _log(f"[transcribe] gemini ok; keys={list(result.keys())}")

    except CommandError as e:
        _log(f"[transcribe][FETCH/REMUX ERROR] {e}")
        raise HTTPException(502, f"Fetch/remux error: {e}")
    except Exception as e:
        # any other unexpected error from Gemini / parsing
        _log(f"[transcribe][ERROR] {e.__class__.__name__}: {e}")
        raise HTTPException(502, f"Transcription error: {e}")
    finally:
        if temp_path is not None:
            safe_unlink(temp_path)
            _log("[transcribe] temp file cleaned")

    import json

    if isinstance(result, dict):
        text = json.dumps(result, ensure_ascii=False)  # <- stringify dict
    else:
        text = str(result)

    if not text.strip():
        raise HTTPException(502, "Empty transcript returned")

    if not text:
        _log("[transcribe] ERROR: empty transcript returned")
        raise HTTPException(502, "Empty transcript returned")

    # 4) Upsert into transcripts
    try:
        t = db.get(Transcript, video_id)
        if t is None:
            t = Transcript(video_id=video_id, text=text)
            db.add(t)
            _log("[transcribe] creating new transcript row")
        else:
            t.text = text
            _log("[transcribe] updating existing transcript row")

        db.flush()
        db.commit()
        _log(f"[transcribe] saved transcript video_id={video_id}, chars={len(text)}")

    except SQLAlchemyError as e:
        db.rollback()
        _log(f"[transcribe][DB ERROR] {e.__class__.__name__}: {e}")
        raise HTTPException(500, f"DB error saving transcript: {e.__class__.__name__}: {e}")

    return TranscriptOut(
        video_id=video_id,
        title=v.title,
        url=v.url,
        media_path=v.media_path,
        text=t.text,
    )


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
