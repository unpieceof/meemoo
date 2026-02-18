"""Configuration from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Optional
VERBOSE_DEFAULT = os.environ.get("VERBOSE_DEFAULT", "0") == "1"
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
MAX_EXTRACT_CHARS = int(os.environ.get("MAX_EXTRACT_CHARS", "4000"))
