#!/usr/bin/env python3
"""
Migration: Add collections table
"""
import sys
sys.path.insert(0, '.')

from app.db import engine
from sqlalchemy import text

def migrate():
    print("Creating collections table...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS collections (
        id VARCHAR PRIMARY KEY,
        query TEXT NOT NULL,
        ai_answer TEXT,
        video_ids JSONB DEFAULT '[]'::jsonb,
        metadata_json JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX IF NOT EXISTS idx_collections_created_at ON collections(created_at DESC);
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    
    print("✅ Collections table created!")

if __name__ == "__main__":
    migrate()
