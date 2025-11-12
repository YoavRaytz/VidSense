from sqlalchemy import Column, String, Integer, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from db import Base

class Video(Base):
    __tablename__ = 'videos'
    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)   # caption/description
    clip_count = Column(Integer, nullable=False, default=1)

    author = Column(String, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    lang = Column(String, default='en')
    media_path = Column(String, nullable=True)
    hashtags = Column(JSONB, default=list)
    metadata_json = Column(JSONB, default=dict)
    created_at = Column(DateTime, server_default=func.now())

class Transcript(Base):
    __tablename__ = 'transcripts'
    video_id = Column(String, primary_key=True)
    text = Column(Text, nullable=True)
    ocr_json = Column(JSONB, default=list)
    summary = Column(Text, nullable=True)
    embedding = Column(Vector(384))
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

class Collection(Base):
    __tablename__ = 'collections'
    id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)  # Original search query
    ai_answer = Column(Text, nullable=True)  # AI-generated answer
    video_ids = Column(JSONB, default=list)  # List of relevant video IDs
    metadata_json = Column(JSONB, default=dict)  # Additional metadata (scores, etc.)
    created_at = Column(DateTime, server_default=func.now())

