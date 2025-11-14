-- Add query_embedding column to collections table
ALTER TABLE collections ADD COLUMN IF NOT EXISTS query_embedding vector(384);

-- Create retrieval_feedback table
CREATE TABLE IF NOT EXISTS retrieval_feedback (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    query_embedding vector(384),
    video_id VARCHAR NOT NULL,
    feedback VARCHAR NOT NULL CHECK (feedback IN ('good', 'bad')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on query_embedding for similarity search
CREATE INDEX IF NOT EXISTS collections_query_embedding_idx 
ON collections USING hnsw (query_embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS retrieval_feedback_query_embedding_idx 
ON retrieval_feedback USING hnsw (query_embedding vector_cosine_ops);

-- Create index for faster feedback lookups
CREATE INDEX IF NOT EXISTS retrieval_feedback_query_idx ON retrieval_feedback(query);
CREATE INDEX IF NOT EXISTS retrieval_feedback_video_idx ON retrieval_feedback(video_id);
