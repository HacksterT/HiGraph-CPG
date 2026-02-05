"""LLM-powered answer generation with citations."""

import time

import httpx

from api.config import Settings, get_settings

# Answer generation prompt template
ANSWER_PROMPT = """You are a clinical decision support assistant helping physicians with Type 2 Diabetes treatment decisions based on the VA/DoD Clinical Practice Guideline.

IMPORTANT RULES:
1. ONLY use information from the provided recommendations below - never make up or invent recommendations
2. Always cite specific recommendation IDs (e.g., "Recommendation 22" or "REC_022")
3. Include the strength (Strong/Weak) and direction (For/Against) when discussing recommendations
4. If the provided context doesn't contain relevant information, say "Based on the available recommendations, I don't have specific guidance on this topic."
5. Keep answers concise but complete (2-3 paragraphs max)
6. Use markdown formatting: **bold** for recommendation IDs and key terms
7. When multiple recommendations apply, prioritize Strong recommendations over Weak ones

RETRIEVED RECOMMENDATIONS:
{context}

PHYSICIAN'S QUESTION:
{question}

Provide a helpful, accurate answer that cites the specific recommendations:"""

NO_RESULTS_RESPONSE = """Based on the available recommendations in the VA/DoD Type 2 Diabetes Clinical Practice Guideline, I don't have specific guidance that directly addresses your question.

You may want to:
- Rephrase your question with different terms
- Ask about a specific aspect of diabetes management (e.g., medications, glycemic targets, comorbidities)
- Consult the full guideline document for comprehensive information"""


class AnswerGenerator:
    """Generates natural language answers from retrieved recommendations."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.Client | None = None
        self.model = "claude-3-5-sonnet-20241022"  # Better quality for synthesis

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client for Anthropic API."""
        if self._client is None:
            self._client = httpx.Client(
                base_url="https://api.anthropic.com",
                headers={
                    "x-api-key": self.settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=60.0,  # Longer timeout for generation
            )
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def generate(
        self,
        question: str,
        recommendations: list[dict],
        include_studies: bool = False,
    ) -> tuple[str, dict, int]:
        """
        Generate a natural language answer from retrieved recommendations.

        Args:
            question: The user's question
            recommendations: List of recommendation dicts from query endpoint
            include_studies: Whether to include study details in context

        Returns:
            Tuple of (answer_text, token_usage, generation_time_ms)
        """
        start_time = time.perf_counter()

        # Handle no results case
        if not recommendations:
            return NO_RESULTS_RESPONSE, {"prompt": 0, "completion": 0}, 0

        # Build context from recommendations
        context = self._build_context(recommendations, include_studies)

        # Check context length and truncate if needed
        context = self._truncate_context(context, max_tokens=6000)

        # Build prompt
        prompt = ANSWER_PROMPT.format(context=context, question=question)

        try:
            response = self.client.post(
                "/v1/messages",
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            result = response.json()

            # Extract answer text
            answer = result["content"][0]["text"]

            # Extract token usage
            usage = result.get("usage", {})
            tokens = {
                "prompt": usage.get("input_tokens", 0),
                "completion": usage.get("output_tokens", 0),
            }

        except httpx.HTTPError as e:
            # Return error message instead of failing
            answer = f"I apologize, but I encountered an error generating the answer. Please try again. (Error: {type(e).__name__})"
            tokens = {"prompt": 0, "completion": 0}

        generation_time_ms = int((time.perf_counter() - start_time) * 1000)
        return answer, tokens, generation_time_ms

    def _build_context(
        self,
        recommendations: list[dict],
        include_studies: bool = False,
    ) -> str:
        """Build context string from recommendations."""
        context_parts = []

        for i, rec in enumerate(recommendations, 1):
            rec_id = rec.get("rec_id", f"REC_{i}")
            rec_text = rec.get("rec_text", "No text available")
            strength = rec.get("strength", "Unknown")
            direction = rec.get("direction", "Unknown")
            topic = rec.get("topic", "General")
            score = rec.get("score", rec.get("similarity_score", 0))

            part = f"""
---
**Recommendation {rec_id}**
- Topic: {topic}
- Strength: {strength}
- Direction: {direction}
- Relevance Score: {score:.2f}

Text: {rec_text}
"""
            # Add evidence quality if available
            if rec.get("evidence_quality"):
                part += f"- Evidence Quality: {rec['evidence_quality']}\n"
            if rec.get("study_count"):
                part += f"- Supporting Studies: {rec['study_count']}\n"

            context_parts.append(part)

        return "\n".join(context_parts)

    def _truncate_context(self, context: str, max_tokens: int = 6000) -> str:
        """
        Truncate context if it exceeds token limit.

        Uses rough estimate of 4 characters per token.
        """
        max_chars = max_tokens * 4
        if len(context) <= max_chars:
            return context

        # Truncate and add indicator
        truncated = context[:max_chars]
        # Try to end at a recommendation boundary
        last_boundary = truncated.rfind("\n---\n")
        if last_boundary > max_chars * 0.5:
            truncated = truncated[:last_boundary]

        return truncated + "\n\n[Additional recommendations truncated for brevity]"


# Singleton instance
_answer_generator: AnswerGenerator | None = None


def get_answer_generator() -> AnswerGenerator:
    """Get the singleton AnswerGenerator instance."""
    global _answer_generator
    if _answer_generator is None:
        _answer_generator = AnswerGenerator(get_settings())
    return _answer_generator
