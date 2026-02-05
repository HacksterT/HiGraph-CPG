"""Embedding service for query text vectorization.

Note: For the MVP, we use Neo4j's GenAI plugin to generate embeddings server-side.
This service is provided as an alternative for cases where client-side embedding
is preferred (e.g., caching, preprocessing).
"""

import time

import httpx

from api.config import Settings, get_settings


class EmbeddingService:
    """Service for generating text embeddings via OpenAI API."""

    OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def embed_text(self, text: str) -> tuple[list[float], int]:
        """
        Generate embedding for a single text string.

        Args:
            text: The text to embed

        Returns:
            Tuple of (embedding vector, time in ms)
        """
        start_time = time.perf_counter()

        response = await self.client.post(
            self.OPENAI_EMBEDDING_URL,
            json={
                "input": text,
                "model": self.settings.embedding_model,
            },
        )
        response.raise_for_status()

        data = response.json()
        embedding = data["data"][0]["embedding"]

        time_ms = int((time.perf_counter() - start_time) * 1000)
        return embedding, time_ms

    async def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            Tuple of (list of embedding vectors, time in ms)
        """
        start_time = time.perf_counter()

        response = await self.client.post(
            self.OPENAI_EMBEDDING_URL,
            json={
                "input": texts,
                "model": self.settings.embedding_model,
            },
        )
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]

        time_ms = int((time.perf_counter() - start_time) * 1000)
        return embeddings, time_ms


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(get_settings())
    return _embedding_service
