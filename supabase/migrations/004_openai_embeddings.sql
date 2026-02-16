-- Switch from voyage-3-lite (512) to OpenAI text-embedding-3-small (1536)
ALTER TABLE memos DROP COLUMN IF EXISTS embedding;
ALTER TABLE memos ADD COLUMN embedding vector(1536);

-- Add raw_content column for storing extracted text
ALTER TABLE memos ADD COLUMN IF NOT EXISTS raw_content TEXT DEFAULT '';

-- Recreate match function with 1536 dims
CREATE OR REPLACE FUNCTION match_memos(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.2,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid, title text, summary_bullets text[], category text,
    tags text[], source_url text, source_type text,
    created_at timestamptz, similarity float
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT m.id, m.title, m.summary_bullets, m.category, m.tags,
           m.source_url, m.source_type, m.created_at,
           1 - (m.embedding <=> query_embedding) AS similarity
    FROM memos m
    WHERE m.embedding IS NOT NULL
      AND 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END; $$;

-- Helper for partial UUID lookup (cast uuid to text)
CREATE OR REPLACE FUNCTION find_memo_by_prefix(prefix text)
RETURNS SETOF memos
LANGUAGE sql STABLE AS $$
    SELECT * FROM memos WHERE id::text LIKE prefix || '%' LIMIT 1;
$$;
