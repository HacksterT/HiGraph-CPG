"""LLM-powered query router for intelligent retrieval strategy selection."""

import json
import time
from typing import Any

import httpx

from api.config import Settings, get_settings
from api.models.query import (
    ExtractedEntities,
    Intent,
    QueryType,
    RoutingDecision,
)

# Router prompt template
ROUTER_PROMPT = """You are a query router for a clinical practice guideline knowledge graph about Type 2 Diabetes.

Your job is to analyze the user's question and decide the best retrieval strategy:
- VECTOR: ONLY for vague, open-ended questions without specific conditions, medications, or topics (e.g., "Tell me about diabetes management", "What should I know?")
- GRAPH: For ANY question mentioning specific conditions, medications, interventions, topics, recommendation IDs, or care phases (e.g., "What about CKD?", "SGLT2 options?", "What interventions for kidney disease?", "Pharmacotherapy recommendations?")
- HYBRID: For complex patient scenarios with MULTIPLE conditions or characteristics (e.g., "Patient with CKD AND heart failure", "Elderly patient with kidney disease and cardiovascular risk")

IMPORTANT: Prefer GRAPH over VECTOR when the question mentions ANY of these:
- Conditions/comorbidities: CKD, kidney disease, CVD, heart failure, retinopathy, neuropathy, etc.
- Medications/interventions: metformin, SGLT2, GLP-1, insulin, lifestyle, etc.
- Topics: pharmacotherapy, glycemic control, screening, self-management
- Care phases: treatment, diagnosis, screening, prevention, follow-up
- Specific allergies or contraindications to medications

Available graph templates:
- recommendation_only: Fetch specific recommendations by ID
- recommendation_with_evidence: Get recommendations with evidence quality ratings
- evidence_chain_full: Trace from recommendation to evidence to studies
- studies_for_recommendation: Get all studies supporting a recommendation
- recommendations_by_topic: Filter by topic (e.g., Pharmacotherapy, Glycemic Control, Prediabetes)
- recommendations_by_care_phase: Filter by care phase (screening, diagnosis, treatment, complications, comorbidities, follow-up)
- recommendations_by_condition: Filter by comorbidity/condition (CKD, CVD, heart failure, retinopathy, neuropathy, etc.)
- recommendations_by_intervention: Filter by medication/intervention (SGLT2i, GLP-1 RA, metformin, insulin, etc.)
- disease_progression: Show what conditions can develop from a given condition
- care_phases_overview: List all care phases with counts (for navigation)
- conditions_overview: List all conditions with counts (for navigation)
- interventions_overview: List all interventions with counts (for navigation)

Clinical topics in the knowledge graph:
- Pharmacotherapy (medications, drug therapy)
- Glycemic Control (blood sugar targets, HbA1c)
- Prediabetes (prevention, lifestyle)
- Comorbidities (heart disease, kidney disease)
- Self-Management (patient education, monitoring)

Care phases available:
- Screening & Prevention, Diagnosis, Treatment, Complication Management, Comorbidity Management, Follow-up

Conditions in the graph:
- Diabetic Kidney Disease (DKD/CKD), Cardiovascular Disease (CVD/ASCVD), Heart Failure, Retinopathy, Neuropathy, Prediabetes, etc.

Interventions/medications in the graph:
- SGLT2 Inhibitors, GLP-1 Receptor Agonists, Metformin, Insulin, Sulfonylureas, DPP-4 Inhibitors, Lifestyle Modification, etc.

Analyze the question and respond with a JSON object:
{{
    "query_type": "VECTOR" | "GRAPH" | "HYBRID",
    "intent": "treatment_recommendation" | "evidence_lookup" | "drug_info" | "safety_check" | "general_question",
    "confidence": 0.0-1.0,
    "entities": {{
        "conditions": ["list of medical conditions mentioned"],
        "medications": ["list of medications mentioned"],
        "patient_characteristics": ["list of patient characteristics"],
        "rec_ids": ["list of recommendation IDs like REC_001, REC_022"],
        "topics": ["list of clinical topics"]
    }},
    "template_hint": "template name if GRAPH or HYBRID, null otherwise",
    "reasoning": "Brief explanation of your routing decision"
}}

User question: {question}

Respond with only the JSON object, no other text."""


class QueryRouter:
    """Routes queries to appropriate retrieval strategies using LLM."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.Client | None = None

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
                timeout=30.0,
            )
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def route(self, question: str) -> tuple[RoutingDecision, int]:
        """
        Analyze a question and determine the best retrieval strategy.

        Args:
            question: The user's natural language question

        Returns:
            Tuple of (RoutingDecision, routing_time_ms)
        """
        start_time = time.perf_counter()

        prompt = ROUTER_PROMPT.format(question=question)

        try:
            response = self.client.post(
                "/v1/messages",
                json={
                    "model": self.settings.router_model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            result = response.json()

            # Extract the text content
            content = result["content"][0]["text"]

            # Parse the JSON response
            decision_data = self._parse_response(content)
            decision = self._build_decision(decision_data)

        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            # Fallback to VECTOR search if routing fails
            decision = RoutingDecision(
                query_type=QueryType.VECTOR,
                intent=Intent.GENERAL_QUESTION,
                confidence=0.5,
                entities=ExtractedEntities(),
                template_hint=None,
                reasoning=f"Routing failed ({type(e).__name__}), defaulting to vector search",
            )

        routing_time_ms = int((time.perf_counter() - start_time) * 1000)
        return decision, routing_time_ms

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse the LLM response, handling potential formatting issues."""
        # Try to extract JSON from the response
        content = content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (```json and ```)
            json_lines = [line for line in lines[1:-1] if not line.startswith("```")]
            content = "\n".join(json_lines)

        return json.loads(content)

    def _build_decision(self, data: dict[str, Any]) -> RoutingDecision:
        """Build a RoutingDecision from parsed JSON data."""
        # Map string values to enums
        query_type = QueryType(data.get("query_type", "VECTOR"))
        intent_str = data.get("intent", "general_question")
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.GENERAL_QUESTION

        # Extract entities
        entities_data = data.get("entities", {})
        entities = ExtractedEntities(
            conditions=entities_data.get("conditions", []),
            medications=entities_data.get("medications", []),
            patient_characteristics=entities_data.get("patient_characteristics", []),
            rec_ids=entities_data.get("rec_ids", []),
            topics=entities_data.get("topics", []),
        )

        return RoutingDecision(
            query_type=query_type,
            intent=intent,
            confidence=float(data.get("confidence", 0.8)),
            entities=entities,
            template_hint=data.get("template_hint"),
            reasoning=data.get("reasoning", "No reasoning provided"),
        )


# Singleton instance
_query_router: QueryRouter | None = None


def get_query_router() -> QueryRouter:
    """Get the singleton QueryRouter instance."""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter(get_settings())
    return _query_router
