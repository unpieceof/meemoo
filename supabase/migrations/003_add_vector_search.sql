-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column (Voyage voyage-3-lite = 512 dims)
ALTER TABLE memos ADD COLUMN IF NOT EXISTS embedding vector(512);

-- Similarity search function
CREATE OR REPLACE FUNCTION match_memos(
    query_embedding vector(512),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    summary_bullets text[],
    category text,
    tags text[],
    source_url text,
    source_type text,
    created_at timestamptz,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id, m.title, m.summary_bullets, m.category, m.tags,
        m.source_url, m.source_type, m.created_at,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM memos m
    WHERE m.embedding IS NOT NULL
      AND 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Dedup function: find by source_url
CREATE OR REPLACE FUNCTION find_by_url(url text)
RETURNS SETOF memos
LANGUAGE sql STABLE
AS $$
    SELECT * FROM memos WHERE source_url = url LIMIT 1;
$$;
