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

    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost", "http://localhost:18000"]


settings = Settings()
