from pydantic import BaseModel
from typing import List, Optional

class IngestFolderRequest(BaseModel):
    base_dir: str
    source: str = 'instagram'

class IngestResponse(BaseModel):
    video_id: str
    status: str

class SearchRequest(BaseModel):
    query: str
    k: int = 10

class SearchHit(BaseModel):
    video_id: str
    title: Optional[str]
    url: str
    score: float
    snippet: str
    media_path: Optional[str] = None

class SearchResponse(BaseModel):
    hits: List[SearchHit]

class TranscriptOut(BaseModel):
    video_id: str
    title: Optional[str]
    url: str
    media_path: Optional[str]
    text: str

class TranscriptUpdate(BaseModel):
    text: str
