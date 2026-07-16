from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM (Ollama, OpenAI-compatible interface)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # Claude API — inert placeholders for a future phase (RF-23). Adding Claude
    # later is a config change, not a code change: set the key, flip the flag.
    claude_api_key: str | None = None
    claude_model: str = "claude-3-5-sonnet-20241022"
    use_classifier: bool = False

    # -- Gamification --------------------------------------------------------
    # PROVISIONAL VALUES — pending finalization with Dra. Grajales per RF-24.
    # These are placeholders to enable end-to-end system testing. Adjust before
    # the pilot. They live here (and in badges.criteria_json) precisely so the
    # numbers can change without touching gamification_service code.
    gamification_xp_per_message: int = 5              # PROVISIONAL
    gamification_xp_per_correct_answer: int = 15      # PROVISIONAL
    gamification_xp_per_module_completed: int = 100   # PROVISIONAL
    gamification_streak_hours_window: int = 36        # PROVISIONAL

    # Database — unified PostgreSQL with pgvector (relational data + vectors + prompts)
    database_url: str = "postgresql+asyncpg://tutoria:tutoria@localhost:5432/tutoria"

    # Embeddings (RAG). Uses Ollama's native API (/api/embeddings), which is a
    # different base URL than the OpenAI-compatible chat endpoint above.
    # nomic-embed-text produces 768-dim vectors, matching content_chunks.embedding.
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    embedding_timeout: float = 30.0
    # When True, the app refuses to start unless the embedding model is available
    # in Ollama. Kept False in dev so the API (e.g. /docs) is reachable without
    # Ollama; set True in production so a misconfigured RAG stack fails loudly.
    require_embedding_model: bool = False

    # -- Open edX MongoDB gateway (RF-22) ------------------------------------
    # Left unset in dev when Open edX is not reachable; sync is off by default
    # so the app never depends on Open edX being up to start.
    openedx_mongo_url: str | None = None
    openedx_mongo_db: str | None = None
    openedx_sync_enabled: bool = False
    openedx_sync_interval_hours: int = 6

    # Token for the manual admin sync trigger.
    # TODO: replace with proper auth (Open edX JWT / IAM) in a later phase.
    admin_token: str | None = None

    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost", "http://localhost:18000"]


settings = Settings()
