"""Rule-based re-ranking for clinical relevance boosting."""

from typing import Any

# Boost multipliers for rule-based re-ranking
STRENGTH_BOOST = {
    "Strong": 1.2,
    "Weak": 1.0,
    "Neither for nor against": 0.9,
    None: 1.0,
}

QUALITY_BOOST = {
    "High": 1.15,
    "Moderate": 1.05,
    "Low": 0.95,
    "Very Low": 0.85,
    None: 1.0,
}

# Direction boost (For recommendations are typically more actionable)
DIRECTION_BOOST = {
    "For": 1.05,
    "Against": 1.0,
    "Neither": 0.95,
    None: 1.0,
}


def rerank_results(
    results: list[dict[str, Any]],
    base_score_key: str = "similarity_score",
) -> list[dict[str, Any]]:
    """
    Apply rule-based re-ranking to boost clinically relevant results.

    Applies multipliers based on:
    - Recommendation strength (Strong > Weak > Neither)
    - Evidence quality (High > Moderate > Low > Very Low)
    - Direction (For > Against > Neither)

    Args:
        results: List of results with recommendation metadata
        base_score_key: Key for the base score to apply boosts to

    Returns:
        Re-ranked list sorted by boosted score (highest first)
    """
    if not results:
        return []

    scored_results = []
    for result in results:
        # Start with base score
        base_score = result.get(base_score_key) or result.get("_rrf_score") or 0.5

        # Apply strength boost
        strength = result.get("strength")
        strength_multiplier = STRENGTH_BOOST.get(strength, 1.0)

        # Apply quality boost
        quality = result.get("evidence_quality")
        quality_multiplier = QUALITY_BOOST.get(quality, 1.0)

        # Apply direction boost
        direction = result.get("direction")
        direction_multiplier = DIRECTION_BOOST.get(direction, 1.0)

        # Calculate final score
        final_score = base_score * strength_multiplier * quality_multiplier * direction_multiplier

        # Create result with score
        scored_result = result.copy()
        scored_result["score"] = round(min(final_score, 1.0), 4)  # Cap at 1.0
        scored_results.append(scored_result)

    # Sort by final score (descending)
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    return scored_results


def apply_topic_relevance_boost(
    results: list[dict[str, Any]],
    target_topics: list[str],
    boost_factor: float = 1.1,
) -> list[dict[str, Any]]:
    """
    Boost results that match specific topics extracted from the query.

    Args:
        results: List of results with topic field
        target_topics: Topics extracted from the user's query
        boost_factor: Multiplier for matching topics

    Returns:
        Results with topic relevance boost applied
    """
    if not results or not target_topics:
        return results

    target_topics_lower = [t.lower() for t in target_topics]

    boosted = []
    for result in results:
        result_copy = result.copy()
        topic = (result.get("topic") or "").lower()
        subtopic = (result.get("subtopic") or "").lower()

        # Check if result topic matches any target topic
        topic_match = any(
            t in topic or t in subtopic or topic in t or subtopic in t
            for t in target_topics_lower
        )

        if topic_match:
            current_score = result_copy.get("score", 0.5)
            result_copy["score"] = round(min(current_score * boost_factor, 1.0), 4)

        boosted.append(result_copy)

    # Re-sort after boost
    boosted.sort(key=lambda x: x.get("score", 0), reverse=True)

    return boosted
