-- Memo table
CREATE TABLE IF NOT EXISTS memos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    summary_bullets TEXT[] NOT NULL DEFAULT '{}',
    category TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    source_url TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'web',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for search
CREATE INDEX IF NOT EXISTS idx_memos_tags ON memos USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_memos_title ON memos USING GIN (to_tsvector('simple', title));
