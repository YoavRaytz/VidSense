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
from .metadata_extractors import MetadataExtractor
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


class VideoOut(BaseModel):
    id: str
    source: str
    url: str
    title: str | None
    author: str | None
    description: str | None
    clip_count: int
    duration_sec: int | None
    hashtags: list[str] | None
    metadata_json: dict | None
    media_path: str | None
    created_at: str | None

    class Config:
        from_attributes = True


# ---------- routes ----------

@router.get("/", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    """Return all saved videos ordered by created_at desc"""
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    # Convert datetime to string for each video
    result = []
    for v in videos:
        # Safely convert created_at
        created_str = None
        try:
            if v.created_at:
                created_str = v.created_at.isoformat()
        except:
            pass
        
        result.append({
            'id': v.id,
            'source': v.source,
            'url': v.url,
            'title': v.title,
            'author': v.author,
            'description': v.description,
            'clip_count': v.clip_count,
            'duration_sec': v.duration_sec,
            'hashtags': v.hashtags if v.hashtags else [],
            'metadata_json': v.metadata_json if v.metadata_json else {},
            'media_path': v.media_path,
            'created_at': created_str
        })
    return result


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Delete a video and its transcript"""
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")
    
    # Delete transcript if exists
    t = db.get(Transcript, video_id)
    if t:
        db.delete(t)
    
    # Delete video
    db.delete(v)
    db.commit()
    
    return {"message": "Video deleted successfully", "video_id": video_id}


@router.post("/ingest_url")
def ingest_url(payload: IngestURL, db: Session = Depends(get_db)):
    # Check if video already exists
    existing = db.query(Video).filter(Video.url == payload.link).first()
    if existing:
        print(f"[ingest_url] Video already exists: {existing.id}")
        return {
            "video_id": existing.id,
            "title": existing.title,
            "clip_count": existing.clip_count,
            "description": existing.description,
            "author": existing.author,
            "already_exists": True,
            "message": "Video already ingested, returning existing record"
        }
    
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
        # pull metadata using source-specific extractor
        try:
            raw_meta = get_meta(payload.link)
            print(f"[ingest_url] raw metadata keys: {list(raw_meta.keys())}")
            
            # Use source-specific extractor
            extractor = MetadataExtractor(raw_meta)
            extracted = extractor.extract()
            
            print(f"[ingest_url] detected source: {extractor.source}")
            
            # Apply extracted metadata to video object
            v.title = extracted.get("title")
            v.description = extracted.get("description")
            v.clip_count = extracted.get("clip_count", 1)
            v.author = extracted.get("author")
            v.duration_sec = extracted.get("duration_sec")
            v.hashtags = extracted.get("hashtags", [])
            v.metadata_json = extracted.get("metadata_json", {})
            
            print(f"[ingest_url] title='{v.title}', author='{v.author}', "
                  f"hashtags={len(v.hashtags or [])}, "
                  f"platform={v.metadata_json.get('platform') if v.metadata_json else 'unknown'}")
            
        except CommandError as e:
            # non-fatal: still allow ingest
            print(f"[ingest_url][meta warn] {e}")
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(500, f"DB error: {e}")

    return {
        "video_id": v.id,
        "title": v.title,
        "clip_count": v.clip_count,
        "description": v.description,
        "author": v.author,
        "hashtags": v.hashtags,
        "already_exists": False
    }


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
    new_text = ""
    if t:
        old_text = getattr(t, 'text', None) or ""
        new_text = old_text + header + text
        setattr(t, 'text', new_text)
    else:
        new_text = (header + text).lstrip()
        t = Transcript(video_id=video_id)
        setattr(t, 'text', new_text)
        db.add(t)
    
    # Generate and store embedding
    from .embeddings import embed_text, combine_text_for_embedding
    desc_val = getattr(v, 'description', None)
    desc_str = str(desc_val) if desc_val is not None else None
    combined_text = combine_text_for_embedding(new_text, desc_str)
    print(f"[transcribe] generating embedding for {len(combined_text)} chars")
    embedding = embed_text(combined_text)
    setattr(t, 'embedding', embedding)
    
    db.commit()

    # Convert to proper types for response
    v_title = str(getattr(v, 'title', '')) if getattr(v, 'title', None) else None
    v_url = str(getattr(v, 'url', ''))
    v_media_path = str(getattr(v, 'media_path', '')) if getattr(v, 'media_path', None) else None

    return TranscriptOut(video_id=video_id, title=v_title, url=v_url, media_path=v_media_path, text=new_text)



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

    t_text = str(getattr(t, 'text', ''))
    _log(f"[get_transcript] ok chars={len(t_text)}")
    
    v_title = str(getattr(v, 'title', '')) if getattr(v, 'title', None) else None
    v_url = str(getattr(v, 'url', ''))
    v_media_path = str(getattr(v, 'media_path', '')) if getattr(v, 'media_path', None) else None
    
    return TranscriptOut(
        video_id=video_id,
        title=v_title,
        url=v_url,
        media_path=v_media_path,
        text=t_text,
    )


@router.put("/{video_id}/transcript")
def put_transcript(video_id: str, payload: TranscriptUpdate, db: Session = Depends(get_db)):
    _log(f"[put_transcript] video_id={video_id} chars={len(payload.text or '')}")

    v = db.get(Video, video_id)
    if not v:
        _log("[put_transcript] 404 video not found")
        raise HTTPException(404, "Video not found")

    try:
        # Generate embedding for the transcript + caption
        from .embeddings import embed_text, combine_text_for_embedding
        desc_val = getattr(v, 'description', None)
        desc_str = str(desc_val) if desc_val is not None else None
        combined_text = combine_text_for_embedding(payload.text, desc_str)
        _log(f"[put_transcript] generating embedding for {len(combined_text)} chars")
        embedding = embed_text(combined_text)
        
        t = db.get(Transcript, video_id)
        if t is None:
            t = Transcript(video_id=video_id)
            setattr(t, 'text', payload.text or "")
            setattr(t, 'embedding', embedding)
            db.add(t)
            _log("[put_transcript] creating new transcript row with embedding")
        else:
            setattr(t, 'text', payload.text or "")
            setattr(t, 'embedding', embedding)
            _log("[put_transcript] updating transcript row with new embedding")

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
