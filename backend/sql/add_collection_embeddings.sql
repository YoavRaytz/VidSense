-- Add query_embedding column to collections table for semantic similarity search
-- Run this migration to add embeddings support to existing collections

ALTER TABLE collections 
ADD COLUMN IF NOT EXISTS query_embedding vector(384);

-- Create index for fast similarity search
CREATE INDEX IF NOT EXISTS collections_query_embedding_idx 
ON collections USING hnsw (query_embedding vector_cosine_ops);

-- Note: Run backfill_collection_embeddings.py after this migration
-- to generate embeddings for existing collections
