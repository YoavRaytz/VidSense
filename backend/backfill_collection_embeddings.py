#!/usr/bin/env python3
"""
Backfill query embeddings for existing collections.
Run this script to generate embeddings for collections that were saved without embeddings.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal, engine
from app.models import Collection
from app.embeddings import embed_text
from sqlalchemy import text

def backfill_embeddings():
    """Generate embeddings for all collections that don't have them"""
    db = SessionLocal()
    
    try:
        # Get collections without embeddings
        collections = db.query(Collection).filter(Collection.query_embedding == None).all()
        
        print(f"Found {len(collections)} collections without embeddings")
        
        updated_count = 0
        for collection in collections:
            try:
                print(f"Processing collection: {collection.id} - '{collection.query}'")
                
                # Generate embedding
                embedding = embed_text(collection.query)
                
                # Update collection
                collection.query_embedding = embedding
                db.commit()
                
                updated_count += 1
                print(f"  ✓ Updated (embedding dim: {len(embedding)})")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                db.rollback()
                continue
        
        print(f"\n✅ Successfully updated {updated_count}/{len(collections)} collections")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Backfilling Collection Embeddings")
    print("=" * 60)
    backfill_embeddings()
