import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SUPABASE_URL: str = os.environ["SUPABASE_URL"]
    SUPABASE_SERVICE_ROLE_KEY: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

    GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    CHUNK_SIZE: int = 800          # characters per chunk
    CHUNK_OVERLAP: int = 150

    # Auto-save fires a PATCH every couple of seconds while typing. Only take a
    # version snapshot if the newest one is at least this old, so a whole editing
    # session collapses into a handful of restore points instead of hundreds.
    VERSION_MIN_INTERVAL_SECONDS: int = int(os.environ.get("VERSION_MIN_INTERVAL_SECONDS", "600"))

    # Supabase Auth lookups (network call) are cached per token for this long.
    AUTH_CACHE_TTL_SECONDS: int = int(os.environ.get("AUTH_CACHE_TTL_SECONDS", "30"))


settings = Settings()
