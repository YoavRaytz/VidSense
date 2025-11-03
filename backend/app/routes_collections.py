from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4
from typing import List, Optional

from .db import get_db
from .models import Collection, Video

router = APIRouter(prefix="/collections", tags=["collections"])


# ---------- Schemas ----------

class CollectionCreate(BaseModel):
    query: str
    ai_answer: Optional[str] = None
    video_ids: List[str] = []
    metadata_json: dict = {}


class CollectionOut(BaseModel):
    id: str
    query: str
    ai_answer: Optional[str]
    video_ids: List[str]
    metadata_json: dict
    created_at: str

    class Config:
        from_attributes = True


class CollectionWithVideos(BaseModel):
    id: str
    query: str
    ai_answer: Optional[str]
    videos: List[dict]  # Full video objects
    metadata_json: dict
    created_at: str


# ---------- Routes ----------

@router.post("/", response_model=CollectionOut)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    """Save a search result to collections"""
    collection_id = uuid4().hex
    
    collection = Collection(
        id=collection_id,
        query=payload.query,
        ai_answer=payload.ai_answer,
        video_ids=payload.video_ids,
        metadata_json=payload.metadata_json,
    )
    
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    return {
        "id": collection.id,
        "query": collection.query,
        "ai_answer": collection.ai_answer,
        "video_ids": collection.video_ids,
        "metadata_json": collection.metadata_json,
        "created_at": collection.created_at.isoformat() if collection.created_at else None,
    }


@router.get("/", response_model=List[CollectionOut])
def list_collections(db: Session = Depends(get_db)):
    """Get all saved collections"""
    collections = db.query(Collection).order_by(Collection.created_at.desc()).all()
    
    return [
        {
            "id": c.id,
            "query": c.query,
            "ai_answer": c.ai_answer,
            "video_ids": c.video_ids or [],
            "metadata_json": c.metadata_json or {},
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in collections
    ]


@router.get("/{collection_id}", response_model=CollectionWithVideos)
def get_collection(collection_id: str, db: Session = Depends(get_db)):
    """Get a specific collection with full video details"""
    collection = db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    
    # Fetch all videos for this collection
    video_ids = collection.video_ids or []
    videos = db.query(Video).filter(Video.id.in_(video_ids)).all() if video_ids else []
    
    # Create a mapping of video_id to video object
    video_map = {v.id: v for v in videos}
    
    # Get source data from metadata if available
    sources_data = collection.metadata_json.get('sources', []) if collection.metadata_json else []
    sources_map = {s['video_id']: s for s in sources_data}
    
    # Return videos in the same order as video_ids, with scores
    videos_data = []
    for vid in video_ids:
        v = video_map.get(vid)
        if v:
            source_info = sources_map.get(vid, {})
            videos_data.append({
                "id": v.id,
                "title": v.title,
                "author": v.author,
                "description": v.description,
                "url": v.url,
                "source": v.source,
                "duration_sec": v.duration_sec,
                "clip_count": v.clip_count,
                "hashtags": v.hashtags or [],
                "metadata_json": v.metadata_json or {},
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "score": source_info.get('score'),
                "snippet": source_info.get('snippet'),
            })
    
    return {
        "id": collection.id,
        "query": collection.query,
        "ai_answer": collection.ai_answer,
        "videos": videos_data,
        "metadata_json": collection.metadata_json or {},
        "created_at": collection.created_at.isoformat() if collection.created_at else None,
    }


@router.delete("/{collection_id}")
def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    """Delete a collection"""
    collection = db.get(Collection, collection_id)
    if not collection:
        raise HTTPException(404, "Collection not found")
    
    db.delete(collection)
    db.commit()
    
    return {"message": "Collection deleted successfully", "collection_id": collection_id}
