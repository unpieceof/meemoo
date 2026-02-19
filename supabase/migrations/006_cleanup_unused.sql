-- Drop unused vector search infrastructure
-- embedding column: added in 003/004 but never populated or queried by the app
ALTER TABLE memos DROP COLUMN IF EXISTS embedding;

-- match_memos: vector similarity search function, never called from app code
DROP FUNCTION IF EXISTS match_memos(vector, float, int);

-- find_by_url: superseded by direct query in supabase_client.py (find_by_url method)
DROP FUNCTION IF EXISTS find_by_url(text);

-- pgvector extension no longer needed
DROP EXTENSION IF EXISTS vector;
