"""HTTP client for Query API communication."""

import httpx
from typing import Optional


def check_api_health(api_url: str, timeout: float = 5.0) -> bool:
    """
    Check if the API is healthy and responding.

    Args:
        api_url: Base URL of the API (e.g., http://localhost:8100)
        timeout: Request timeout in seconds

    Returns:
        True if API is healthy, False otherwise
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{api_url}/health")
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


def get_answer(
    api_url: str,
    question: str,
    include_citations: bool = True,
    include_studies: bool = False,
    timeout: float = 30.0,
) -> dict:
    """
    Get an answer from the Query API.

    Args:
        api_url: Base URL of the API
        question: The question to ask
        include_citations: Whether to include recommendation citations
        include_studies: Whether to include study citations
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'answer', 'citations', 'studies_cited', 'reasoning'
        or dict with 'error' key if request failed
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{api_url}/api/v1/answer",
                json={
                    "question": question,
                    "include_citations": include_citations,
                    "include_studies": include_studies,
                },
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 422:
                # Validation error
                detail = response.json().get("detail", "Invalid request")
                return {"error": f"Validation error: {detail}"}
            else:
                return {"error": f"API error: {response.status_code}"}

    except httpx.TimeoutException:
        return {"error": "Request timed out. The API may be processing a complex query."}
    except httpx.RequestError as e:
        return {"error": f"Connection error: {str(e)}"}


def get_evidence_chain(
    api_url: str,
    rec_id: str,
    timeout: float = 15.0,
) -> dict:
    """
    Get the full evidence chain for a recommendation.

    Args:
        api_url: Base URL of the API
        rec_id: The recommendation ID to get evidence for
        timeout: Request timeout in seconds

    Returns:
        Response dict with evidence chain data or dict with 'error' key
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{api_url}/api/v1/search/graph",
                json={
                    "template": "evidence_chain_full",
                    "params": {"rec_ids": [rec_id]},
                },
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return {"success": True, "data": results[0]}
                return {"error": "No evidence chain found for this recommendation"}
            else:
                return {"error": f"API error: {response.status_code}"}

    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except httpx.RequestError as e:
        return {"error": f"Connection error: {str(e)}"}


def get_studies_for_recommendation(
    api_url: str,
    rec_id: str,
    timeout: float = 15.0,
) -> dict:
    """
    Get all studies supporting a recommendation with full details (including abstracts).

    Args:
        api_url: Base URL of the API
        rec_id: The recommendation ID
        timeout: Request timeout in seconds

    Returns:
        Response dict with studies list or dict with 'error' key
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{api_url}/api/v1/search/graph",
                json={
                    "template": "studies_for_recommendation",
                    "params": {"rec_id": rec_id},
                },
            )

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "studies": data.get("results", [])}
            else:
                return {"error": f"API error: {response.status_code}"}

    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except httpx.RequestError as e:
        return {"error": f"Connection error: {str(e)}"}
