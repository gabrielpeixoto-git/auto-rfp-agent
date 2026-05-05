from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://autorfppguser:autorfppgpass@localhost:5432/autorfpdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_max_tokens: int = 4096
    openai_temperature: float = 0.1

    # Anthropic (for future use)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Groq (fast inference, free tier available)
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-70b-versatile"
    # Alternatives: "mixtral-8x7b-32768", "gemma-7b-it"

    # Ollama (local LLM - completely free, no API keys needed)
    ollama_base_url: str = "http://host.docker.internal:11434"  # Docker Desktop host access
    ollama_model: str = "llama3.1"  # or "mistral", "codellama"
    ollama_embedding_model: str = "nomic-embed-text"  # for embeddings
    ollama_max_tokens: int = 4096
    ollama_temperature: float = 0.1

    # AI Provider Settings
    default_ai_provider: Literal["openai", "anthropic", "groq", "ollama"] = "ollama"
    embedding_dimensions: int = 768  # nomic-embed-text (Ollama default)

    # File Upload
    max_upload_size_mb: int = 50
    upload_dir: str = "uploads"
    allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".xls", ".txt", ".csv"]

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Retrieval
    retrieval_top_k: int = 10
    similarity_threshold: float = 0.3  # Lowered for testing

    # RAG
    rag_max_context_chunks: int = 5
    rag_max_tokens_per_chunk: int = 2000

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
