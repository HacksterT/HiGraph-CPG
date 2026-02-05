"""
PubMed Metadata Enrichment

Fetches full metadata (abstract, MeSH terms, etc.) for studies with resolved PMIDs.
Caches results to avoid duplicate API calls across guidelines.
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

from Bio import Entrez, Medline


Entrez.email = os.getenv('PUBMED_EMAIL', 'higraph-cpg@example.com')
_api_key = os.getenv('PUBMED_API_KEY')
if _api_key:
    Entrez.api_key = _api_key


def _rate_limit():
    if _api_key:
        time.sleep(0.12)
    else:
        time.sleep(0.4)


def load_metadata_cache(cache_dir: str) -> Dict[str, dict]:
    """Load metadata cache."""
    cache_path = Path(cache_dir) / "metadata_cache.json"
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    return {}


def save_metadata_cache(cache: dict, cache_dir: str):
    """Save metadata cache."""
    cache_path = Path(cache_dir) / "metadata_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=2)


def fetch_pubmed_metadata(pmid: str) -> Optional[dict]:
    """
    Fetch full metadata for a PMID from PubMed.

    Returns dict with: abstract, mesh_terms, publication_types, doi, journal, etc.
    """
    try:
        _rate_limit()
        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="medline", retmode="text")
        records = list(Medline.parse(handle))
        handle.close()

        if not records:
            return None

        record = records[0]

        metadata = {
            'pmid': pmid,
            'title': record.get('TI', ''),
            'abstract': record.get('AB', ''),
            'authors': record.get('AU', []),
            'journal': record.get('JT', '') or record.get('TA', ''),
            'year': '',
            'doi': '',
            'mesh_terms': record.get('MH', []),
            'publication_types': record.get('PT', []),
            'keywords': record.get('OT', []),
        }

        # Parse year from date
        dp = record.get('DP', '')
        if dp:
            metadata['year'] = dp[:4]

        # Parse DOI from article identifiers
        aids = record.get('AID', [])
        for aid in aids:
            if aid.endswith('[doi]'):
                metadata['doi'] = aid.replace(' [doi]', '')
                break

        return metadata

    except Exception as e:
        print(f"  Error fetching PMID {pmid}: {e}")
        return None


def enrich_studies_with_metadata(studies: list, cache_dir: str) -> list:
    """
    Enrich studies that have PMIDs with full PubMed metadata.

    Args:
        studies: List of study dicts
        cache_dir: Path to shared cache

    Returns:
        Updated studies list
    """
    cache = load_metadata_cache(cache_dir)
    enriched = 0
    cached = 0
    failed = 0

    for i, study in enumerate(studies):
        pmid = study.get('pmid')
        if not pmid:
            continue

        # Check cache
        if pmid in cache:
            metadata = cache[pmid]
            _apply_metadata(study, metadata)
            cached += 1
            continue

        # Fetch from PubMed
        metadata = fetch_pubmed_metadata(pmid)
        if metadata:
            cache[pmid] = metadata
            _apply_metadata(study, metadata)
            enriched += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(studies)}")
            save_metadata_cache(cache, cache_dir)

    save_metadata_cache(cache, cache_dir)

    print(f"\nMetadata Enrichment Summary:")
    print(f"  Enriched (new): {enriched}")
    print(f"  From cache: {cached}")
    print(f"  Failed: {failed}")

    return studies


def _apply_metadata(study: dict, metadata: dict):
    """Apply PubMed metadata to a study dict without overwriting existing data."""
    if metadata.get('abstract') and not study.get('abstract'):
        study['abstract'] = metadata['abstract']
    if metadata.get('doi') and not study.get('doi'):
        study['doi'] = metadata['doi']
    if metadata.get('mesh_terms'):
        study['mesh_terms'] = metadata['mesh_terms']
    if metadata.get('publication_types'):
        study['publication_types'] = metadata['publication_types']
    if metadata.get('keywords'):
        study['keywords'] = metadata['keywords']
    if metadata.get('journal') and not study.get('journal'):
        study['journal'] = metadata['journal']


def run(config_path: str):
    """Run metadata enrichment for studies with PMIDs."""
    from scripts.pipeline.config_loader import load_config
    from scripts.pipeline.pipeline_context import PipelineContext

    config = load_config(config_path)
    ctx = PipelineContext(config)

    if not ctx.studies_json.exists():
        print("ERROR: studies.json not found.")
        return None

    with open(ctx.studies_json) as f:
        studies = json.load(f)

    has_pmid = sum(1 for s in studies if s.get('pmid'))
    print("=" * 60)
    print("FETCHING PUBMED METADATA")
    print("=" * 60)
    print(f"Studies with PMIDs: {has_pmid}/{len(studies)}")

    studies = enrich_studies_with_metadata(studies, str(ctx.pubmed_cache_dir))

    with open(ctx.studies_json, 'w') as f:
        json.dump(studies, f, indent=2)
    print(f"\nEnriched studies saved to {ctx.studies_json}")

    return studies


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch PubMed metadata for studies")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
