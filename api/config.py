"""Configuration settings for the Query API."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Neo4j connection
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    # OpenAI API (for embeddings via Neo4j GenAI plugin)
    openai_api_key: str

    # Anthropic API (for query routing LLM)
    anthropic_api_key: str

    # Query router settings
    router_model: str = "claude-3-5-haiku-20241022"  # Fast and cheap for routing

    # API settings
    api_title: str = "HiGraph-CPG Query API"
    api_version: str = "1.0.0"
    api_description: str = "Semantic and structural search over clinical practice guideline knowledge graphs"
    api_port: int = 8100  # Assigned port per C:\Projects\PORTS.md

    # Vector search defaults
    default_top_k: int = 10
    max_top_k: int = 50
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars like PUBMED_API_KEY
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
