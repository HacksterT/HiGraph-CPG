"""
PubMed PMID Resolution

Resolves study citations to PubMed IDs using Bio.Entrez. Rate-limited,
with caching to data/shared/pubmed_cache/ for cross-guideline reuse.
"""

import json
import os
import time
import sys
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

load_dotenv()

from Bio import Entrez


# Configure Entrez
Entrez.email = os.getenv('PUBMED_EMAIL', 'higraph-cpg@example.com')
_api_key = os.getenv('PUBMED_API_KEY')
if _api_key:
    Entrez.api_key = _api_key


def _rate_limit():
    """Sleep to respect PubMed rate limits. 3/sec without key, 10/sec with."""
    if _api_key:
        time.sleep(0.12)  # ~8/sec to stay under 10
    else:
        time.sleep(0.4)  # ~2.5/sec to stay under 3


def load_cache(cache_dir: str) -> Dict[str, dict]:
    """Load the PMID cache from disk."""
    cache_path = Path(cache_dir) / "pmid_cache.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_dir: str):
    """Save the PMID cache to disk."""
    cache_path = Path(cache_dir) / "pmid_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)


def search_pmid(title: str, authors: str = "", year: int = None) -> Optional[str]:
    """
    Search PubMed for a study by title and return its PMID.

    Args:
        title: Study title
        authors: Author names (optional, improves matching)
        year: Publication year (optional, improves matching)

    Returns:
        PMID string if found, None otherwise
    """
    # Build search query
    query_parts = [f'"{title}"[Title]']
    if year:
        query_parts.append(f'{year}[pdat]')
    if authors:
        # Use first author's last name
        first_author = authors.split(',')[0].split(' ')[0].strip()
        if first_author and len(first_author) > 2:
            query_parts.append(f'{first_author}[Author]')

    query = ' AND '.join(query_parts)

    try:
        _rate_limit()
        handle = Entrez.esearch(db="pubmed", term=query, retmax=3)
        results = Entrez.read(handle)
        handle.close()

        id_list = results.get('IdList', [])
        if id_list:
            return id_list[0]

        # Retry with title only (less strict)
        if len(query_parts) > 1:
            _rate_limit()
            handle = Entrez.esearch(db="pubmed", term=f'"{title}"[Title]', retmax=3)
            results = Entrez.read(handle)
            handle.close()
            id_list = results.get('IdList', [])
            if id_list:
                return id_list[0]

    except Exception as e:
        print(f"  PubMed search error: {e}")

    return None


def resolve_pmids_for_studies(studies: list, cache_dir: str) -> list:
    """
    Resolve PMIDs for a list of extracted study citations.

    Args:
        studies: List of study dicts with 'title', 'authors', 'year'
        cache_dir: Path to shared PubMed cache directory

    Returns:
        Updated studies list with 'pmid' field populated where resolved
    """
    cache = load_cache(cache_dir)
    resolved = 0
    already_cached = 0
    failed = 0

    for i, study in enumerate(studies):
        # Skip if already has PMID
        if study.get('pmid'):
            already_cached += 1
            continue

        title = study.get('title', '')
        if not title:
            continue

        # Check cache by title
        cache_key = title.lower().strip()[:100]
        if cache_key in cache:
            study['pmid'] = cache[cache_key]['pmid']
            already_cached += 1
            continue

        # Search PubMed
        pmid = search_pmid(
            title=title,
            authors=study.get('authors', ''),
            year=study.get('year'),
        )

        if pmid:
            study['pmid'] = pmid
            cache[cache_key] = {'pmid': pmid, 'title': title}
            resolved += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(studies)} (resolved: {resolved}, cached: {already_cached}, failed: {failed})")
            save_cache(cache, cache_dir)

    save_cache(cache, cache_dir)

    print(f"\nPMID Resolution Summary:")
    print(f"  Total studies: {len(studies)}")
    print(f"  Resolved (new): {resolved}")
    print(f"  Already had PMID/cached: {already_cached}")
    print(f"  Failed to resolve: {failed}")

    return studies


def run(config_path: str):
    """Run PMID resolution for extracted studies."""
    from scripts.pipeline.config_loader import load_config
    from scripts.pipeline.pipeline_context import PipelineContext

    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.studies_json.exists():
        print("ERROR: studies.json not found. Run extract_studies.py first.")
        return None

    with open(ctx.studies_json) as f:
        studies = json.load(f)

    print("=" * 60)
    print("RESOLVING PUBMED IDs")
    print("=" * 60)
    print(f"Studies to resolve: {len(studies)}")

    studies = resolve_pmids_for_studies(studies, str(ctx.pubmed_cache_dir))

    # Save updated studies
    with open(ctx.studies_json, 'w') as f:
        json.dump(studies, f, indent=2)
    print(f"\nUpdated studies saved to {ctx.studies_json}")

    return studies


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Resolve PMIDs for extracted studies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
