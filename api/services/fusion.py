"""Result fusion for hybrid retrieval using Reciprocal Rank Fusion (RRF)."""

from typing import Any


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    id_key: str = "rec_id",
    k: int = 60,
) -> list[dict[str, Any]]:
    """
    Combine multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank_i)) for each list where the item appears.

    Args:
        ranked_lists: List of ranked result lists (each list is ordered by relevance)
        id_key: Key to use for identifying unique items across lists
        k: Smoothing constant (default 60, as per original RRF paper)

    Returns:
        Fused list sorted by combined RRF score (highest first)
    """
    if not ranked_lists:
        return []

    # Track RRF scores and original items
    scores: dict[str, float] = {}
    items: dict[str, dict[str, Any]] = {}
    sources: dict[str, set[str]] = {}

    for list_idx, ranked_list in enumerate(ranked_lists):
        source_name = "vector" if list_idx == 0 else "graph"

        for rank, item in enumerate(ranked_list, start=1):
            item_id = item.get(id_key)
            if item_id is None:
                continue

            # Calculate RRF contribution from this list
            rrf_contribution = 1.0 / (k + rank)

            # Accumulate score
            if item_id not in scores:
                scores[item_id] = 0.0
                items[item_id] = item.copy()
                sources[item_id] = set()

            scores[item_id] += rrf_contribution
            sources[item_id].add(source_name)

            # Merge additional fields from later lists (prefer non-null values)
            for key, value in item.items():
                if value is not None and items[item_id].get(key) is None:
                    items[item_id][key] = value

    # Build result list with scores and sources
    results = []
    for item_id, item in items.items():
        result = item.copy()
        result["_rrf_score"] = scores[item_id]
        result["_sources"] = sources[item_id]

        # Determine source label
        if len(sources[item_id]) > 1:
            result["source"] = "both"
        else:
            result["source"] = list(sources[item_id])[0]

        results.append(result)

    # Sort by RRF score (descending)
    results.sort(key=lambda x: x["_rrf_score"], reverse=True)

    # Clean up internal fields
    for result in results:
        del result["_rrf_score"]
        del result["_sources"]

    return results


def normalize_vector_results(
    vector_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize vector search results to common format for fusion.

    Vector results have similarity_score, need to be adapted for fusion.
    """
    normalized = []
    for result in vector_results:
        item = {
            "rec_id": result.get("rec_id"),
            "rec_text": result.get("rec_text"),
            "strength": result.get("strength"),
            "direction": result.get("direction"),
            "topic": result.get("topic"),
            "similarity_score": result.get("similarity_score"),
        }
        normalized.append(item)
    return normalized


def normalize_graph_results(
    graph_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize graph query results to common format for fusion.

    Graph results may have nested structures that need flattening.
    """
    normalized = []
    for result in graph_results:
        item = {
            "rec_id": result.get("rec_id"),
            "rec_text": result.get("rec_text"),
            "strength": result.get("strength"),
            "direction": result.get("direction"),
            "topic": result.get("topic"),
        }

        # Extract evidence info if present (from evidence templates)
        if "evidence" in result and isinstance(result["evidence"], dict):
            item["evidence_quality"] = result["evidence"].get("quality_rating")
            item["study_count"] = result["evidence"].get("num_studies")
        elif "quality_rating" in result:
            item["evidence_quality"] = result.get("quality_rating")
            item["study_count"] = result.get("num_studies")

        normalized.append(item)
    return normalized
