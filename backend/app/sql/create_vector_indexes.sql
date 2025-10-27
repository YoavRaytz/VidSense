-- Preferred HNSW (requires pgvector >= 0.6.0)
CREATE INDEX IF NOT EXISTS transcripts_embedding_hnsw
ON transcripts
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- Optional runtime knob during session
-- SET hnsw.ef_search = 80;

-- Fallback IVFFlat (for older pgvector)
-- CREATE INDEX IF NOT EXISTS transcripts_embedding_ivfflat
-- ON transcripts
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 1000);
-- SET ivfflat.probes = 10;

-- Verify usage (replace ... with actual query vector JSON/array)
-- EXPLAIN SELECT * FROM transcripts ORDER BY embedding <=> '[...]' LIMIT 5;