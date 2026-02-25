"""LLM-powered answer generation with citations."""

import time

import httpx

from api.config import Settings, get_settings

# Answer generation prompt template (without conversation history)
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

# Answer generation prompt with conversation history
ANSWER_PROMPT_WITH_HISTORY = """You are a clinical decision support assistant helping physicians with Type 2 Diabetes treatment decisions based on the VA/DoD Clinical Practice Guideline.

IMPORTANT RULES:
1. ONLY use information from the provided recommendations below - never make up or invent recommendations
2. Always cite specific recommendation IDs (e.g., "Recommendation 22" or "REC_022")
3. Include the strength (Strong/Weak) and direction (For/Against) when discussing recommendations
4. If the provided context doesn't contain relevant information, say "Based on the available recommendations, I don't have specific guidance on this topic."
5. Keep answers concise but complete (2-3 paragraphs max)
6. Use markdown formatting: **bold** for recommendation IDs and key terms
7. When multiple recommendations apply, prioritize Strong recommendations over Weak ones
8. Use the conversation history to understand context for follow-up questions (e.g., "tell me more about that", "what about side effects?")

RETRIEVED RECOMMENDATIONS:
{context}

CONVERSATION HISTORY:
{history}

PHYSICIAN'S CURRENT QUESTION:
{question}

Provide a helpful, accurate answer that cites the specific recommendations and takes into account the conversation context:"""

# Summarization prompt for long conversation histories
SUMMARIZE_HISTORY_PROMPT = """Summarize the following conversation between a physician and a clinical assistant about diabetes management. Keep the key clinical topics, recommendations mentioned, and patient characteristics discussed. Be concise (2-3 sentences).

CONVERSATION:
{history}

SUMMARY:"""

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
        self.model = "claude-sonnet-4-20250514"  # Claude Sonnet 4 for synthesis

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
        conversation_history: list[dict] | None = None,
    ) -> tuple[str, dict, int, dict]:
        """
        Generate a natural language answer from retrieved recommendations.

        Args:
            question: The user's question
            recommendations: List of recommendation dicts from query endpoint
            include_studies: Whether to include study details in context
            conversation_history: List of previous conversation turns

        Returns:
            Tuple of (answer_text, token_usage, generation_time_ms, context_usage)
        """
        start_time = time.perf_counter()

        # Initialize context usage tracking
        context_usage = {
            "history_turns_received": len(conversation_history) if conversation_history else 0,
            "history_turns_used": 0,
            "history_summarized": False,
            "estimated_context_tokens": 0,
        }

        # Handle no results case
        if not recommendations:
            return NO_RESULTS_RESPONSE, {"prompt": 0, "completion": 0}, 0, context_usage

        # Build context from recommendations
        context = self._build_context(recommendations, include_studies)

        # Check context length and truncate if needed
        context = self._truncate_context(context, max_tokens=6000)

        # Build prompt with or without history
        if conversation_history:
            history_text, context_usage = self._build_history_context(
                conversation_history, context_usage
            )
            prompt = ANSWER_PROMPT_WITH_HISTORY.format(
                context=context,
                history=history_text,
                question=question
            )
        else:
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
        return answer, tokens, generation_time_ms, context_usage

    def _build_history_context(
        self,
        conversation_history: list[dict],
        context_usage: dict,
        max_turns: int = 10,
        max_tokens: int = 2000,
    ) -> tuple[str, dict]:
        """
        Build conversation history context with sliding window and optional summarization.

        Args:
            conversation_history: List of conversation turns
            context_usage: Dict to update with usage info
            max_turns: Maximum number of turns to include (default 10 = 5 exchanges)
            max_tokens: Maximum tokens for history context

        Returns:
            Tuple of (history_text, updated_context_usage)
        """
        if not conversation_history:
            return "[No previous conversation]", context_usage

        # Apply sliding window - keep last N turns
        if len(conversation_history) > max_turns:
            # We need to summarize older turns
            older_turns = conversation_history[:-max_turns]
            recent_turns = conversation_history[-max_turns:]

            # Summarize older turns
            summary = self._summarize_history(older_turns)
            context_usage["history_summarized"] = True

            # Build history text with summary + recent turns
            history_parts = [f"[Summary of earlier conversation: {summary}]", ""]
            for turn in recent_turns:
                role = turn.get("role", "unknown").capitalize()
                content = turn.get("content", "")
                history_parts.append(f"{role}: {content}")

            context_usage["history_turns_used"] = len(recent_turns)
        else:
            # All turns fit in window
            history_parts = []
            for turn in conversation_history:
                role = turn.get("role", "unknown").capitalize()
                content = turn.get("content", "")
                history_parts.append(f"{role}: {content}")

            context_usage["history_turns_used"] = len(conversation_history)

        history_text = "\n".join(history_parts)

        # Truncate if still too long
        max_chars = max_tokens * 4
        if len(history_text) > max_chars:
            history_text = history_text[-max_chars:]
            # Try to start at a clean line
            first_newline = history_text.find("\n")
            if first_newline > 0 and first_newline < len(history_text) * 0.3:
                history_text = "[...]\n" + history_text[first_newline + 1:]

        context_usage["estimated_context_tokens"] = len(history_text) // 4
        return history_text, context_usage

    def _summarize_history(self, turns: list[dict]) -> str:
        """
        Summarize older conversation turns to save tokens.

        Args:
            turns: List of conversation turns to summarize

        Returns:
            Summary string
        """
        # Build history text for summarization
        history_parts = []
        for turn in turns:
            role = turn.get("role", "unknown").capitalize()
            content = turn.get("content", "")
            history_parts.append(f"{role}: {content}")
        history_text = "\n".join(history_parts)

        # Use a quick API call to summarize
        try:
            response = self.client.post(
                "/v1/messages",
                json={
                    "model": "claude-haiku-4-5-20251001",  # Use fast model for summarization
                    "max_tokens": 150,
                    "messages": [
                        {"role": "user", "content": SUMMARIZE_HISTORY_PROMPT.format(history=history_text)}
                    ],
                },
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"].strip()
        except Exception:
            # Fallback: just note that there was earlier conversation
            return "Earlier discussion about diabetes treatment options."

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
