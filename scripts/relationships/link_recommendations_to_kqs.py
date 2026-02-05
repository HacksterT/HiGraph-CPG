"""
Link Recommendations to Key Questions

Infers LEADS_TO relationships between KeyQuestions and Recommendations
using topic matching, text similarity, and document structure analysis.
Each link gets a confidence score.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def _topic_similarity(rec_topic: str, kq_topic: str) -> float:
    """Compute simple topic overlap score between rec and KQ topics."""
    if not rec_topic or not kq_topic:
        return 0.0

    rec_words = set(rec_topic.lower().split())
    kq_words = set(kq_topic.lower().split())

    if not rec_words or not kq_words:
        return 0.0

    overlap = rec_words & kq_words
    return len(overlap) / max(len(rec_words), len(kq_words))


def _text_similarity(text_a: str, text_b: str) -> float:
    """Compute TF-IDF cosine similarity between two texts."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        if not text_a or not text_b:
            return 0.0

        vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf = vectorizer.fit_transform([text_a, text_b])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return float(sim)
    except ImportError:
        return 0.0


def _build_module_topic_map(config) -> Dict[str, List[str]]:
    """Build a map from topic names to module topics for matching."""
    topic_map = {}
    for mod in config.modules:
        for topic in mod.topics:
            topic_map[topic.lower()] = mod.topics
    return topic_map


def link_recommendations_to_kqs(
    recommendations: list,
    key_questions: list,
    config,
) -> List[dict]:
    """
    Infer LEADS_TO relationships from KQs to Recommendations.

    Uses three strategies:
    1. Topic matching: match rec.topic to kq.topic
    2. Text similarity: cosine similarity between rec_text and question_text
    3. Explicit KQ mentions: check if rec text mentions a KQ number

    Args:
        recommendations: List of recommendation dicts
        key_questions: List of key question dicts
        config: GuidelineConfig

    Returns:
        List of relationship dicts with confidence scores
    """
    relationships = []

    for rec in recommendations:
        rec_num = rec.get('rec_number')
        rec_text = rec.get('rec_text', '')
        rec_topic = rec.get('topic', '')

        best_kq = None
        best_confidence = 0.0
        scores_detail = {}

        for kq in key_questions:
            kq_num = kq.get('kq_number')
            kq_text = kq.get('question_text', '')
            kq_topic = kq.get('topic', '')

            # Strategy 1: Topic matching
            topic_score = _topic_similarity(rec_topic, kq_topic)

            # Strategy 2: Text similarity
            text_score = _text_similarity(rec_text, kq_text)

            # Strategy 3: Explicit KQ mention in rec text
            mention_score = 0.0
            kq_patterns = [f'KQ {kq_num}', f'Key Question {kq_num}', f'question {kq_num}']
            for pattern in kq_patterns:
                if pattern.lower() in rec_text.lower():
                    mention_score = 1.0
                    break

            # Combined confidence (weighted)
            confidence = max(
                topic_score * 0.7 + text_score * 0.3,
                mention_score,
                text_score * 0.5 + topic_score * 0.5,
            )

            if confidence > best_confidence:
                best_confidence = confidence
                best_kq = kq_num
                scores_detail = {
                    'topic_score': round(topic_score, 3),
                    'text_score': round(text_score, 3),
                    'mention_score': round(mention_score, 3),
                }

        if best_kq is not None:
            relationships.append({
                'type': 'LEADS_TO',
                'from_type': 'KeyQuestion',
                'from_number': best_kq,
                'to_type': 'Recommendation',
                'to_number': rec_num,
                'confidence': round(best_confidence, 3),
                'scores': scores_detail,
            })

    return relationships


def run(config_path: str):
    """Run recommendation-to-KQ linking."""
    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.recommendations_json.exists():
        print("ERROR: recommendations.json not found")
        return None
    if not ctx.key_questions_json.exists():
        print("ERROR: key_questions.json not found")
        return None

    with open(ctx.recommendations_json) as f:
        recs = json.load(f)
    with open(ctx.key_questions_json) as f:
        kqs = json.load(f)

    print("=" * 60)
    print("LINKING RECOMMENDATIONS TO KEY QUESTIONS")
    print("=" * 60)
    print(f"Recommendations: {len(recs)}")
    print(f"Key Questions: {len(kqs)}")

    rels = link_recommendations_to_kqs(recs, kqs, config)

    # Summary
    high_conf = sum(1 for r in rels if r['confidence'] >= config.confidence_thresholds.auto_accept)
    med_conf = sum(1 for r in rels if config.confidence_thresholds.flag_for_review <= r['confidence'] < config.confidence_thresholds.auto_accept)
    low_conf = sum(1 for r in rels if r['confidence'] < config.confidence_thresholds.flag_for_review)

    print(f"\nResults:")
    print(f"  Total links: {len(rels)}")
    print(f"  High confidence (>={config.confidence_thresholds.auto_accept}): {high_conf}")
    print(f"  Medium confidence: {med_conf}")
    print(f"  Low confidence (<{config.confidence_thresholds.flag_for_review}): {low_conf}")

    return rels


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Link recommendations to key questions")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
