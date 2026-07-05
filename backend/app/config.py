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

    # Database — unified PostgreSQL with pgvector (relational data + vectors + prompts)
    database_url: str = "postgresql+asyncpg://tutoria:tutoria@localhost:5432/tutoria"

    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost", "http://localhost:18000"]


settings = Settings()
