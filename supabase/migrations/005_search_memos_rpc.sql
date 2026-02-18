-- RPC: keyword search across title, category, raw_content, tags, summary_bullets
CREATE OR REPLACE FUNCTION search_memos(
    query TEXT,
    lim INT DEFAULT 5,
    off INT DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    summary_bullets TEXT[],
    category TEXT,
    tags TEXT[],
    source_url TEXT,
    source_type TEXT,
    created_at TIMESTAMPTZ,
    total_count BIGINT
)
LANGUAGE sql STABLE
AS $$
    WITH matched AS (
        SELECT m.*
        FROM memos m
        WHERE m.title ILIKE '%' || query || '%'
           OR m.category ILIKE '%' || query || '%'
           OR m.raw_content ILIKE '%' || query || '%'
           OR array_to_string(m.tags, ' ') ILIKE '%' || query || '%'
           OR array_to_string(m.summary_bullets, ' ') ILIKE '%' || query || '%'
        ORDER BY m.created_at DESC
    )
    SELECT
        matched.id,
        matched.title,
        matched.summary_bullets,
        matched.category,
        matched.tags,
        matched.source_url,
        matched.source_type,
        matched.created_at,
        (SELECT count(*) FROM matched) AS total_count
    FROM matched
    OFFSET off
    LIMIT lim;
$$;
