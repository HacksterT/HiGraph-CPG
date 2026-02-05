"""
Pipeline Orchestrator

Single entry point that runs all pipeline phases in sequence.
Supports --start-from and --stop-after for partial runs.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


STAGES = [
    'preprocess',
    'extract_metadata',
    'extract_recommendations',
    'extract_key_questions',
    'extract_evidence_bodies',
    'extract_studies',
    'resolve_pmids',
    'fetch_metadata',
    'build_relationships',
    'populate_graph',
    'generate_embeddings',
    'validate',
]


def run_stage(stage: str, config_path: str, ctx: PipelineContext):
    """Run a single pipeline stage."""
    print(f"\n{'='*60}")
    print(f"STAGE: {stage}")
    print(f"{'='*60}\n")

    if stage == 'preprocess':
        from scripts.pdf_preprocessing.extract_toc import run as run_toc
        from scripts.pdf_preprocessing.extract_tables import run as run_tables
        from scripts.pdf_preprocessing.split_sections import run as run_split
        from scripts.pdf_preprocessing.convert_to_markdown import run as run_convert

        run_toc(config_path)
        run_tables(config_path)
        run_split(config_path)
        run_convert(config_path)

    elif stage == 'extract_metadata':
        from scripts.extraction.extract_guideline_metadata import run
        run(config_path)

    elif stage == 'extract_recommendations':
        from scripts.extraction.extract_recommendations import run
        run(config_path)

    elif stage == 'extract_key_questions':
        from scripts.extraction.extract_key_questions import run
        run(config_path)

    elif stage == 'extract_evidence_bodies':
        from scripts.extraction.extract_evidence_bodies import run
        run(config_path)

    elif stage == 'extract_studies':
        from scripts.extraction.extract_studies import run
        run(config_path)

    elif stage == 'resolve_pmids':
        from scripts.pubmed.resolve_pmids import run
        run(config_path)

    elif stage == 'fetch_metadata':
        from scripts.pubmed.fetch_metadata import run
        run(config_path)

    elif stage == 'build_relationships':
        from scripts.relationships.build_all_relationships import run
        run(config_path)

    elif stage == 'populate_graph':
        from scripts.graph_population.populate_guideline import run as run_gl
        from scripts.graph_population.populate_clinical_modules import run as run_cm
        from scripts.graph_population.populate_recommendations import run as run_rec
        from scripts.graph_population.populate_key_questions import run as run_kq
        from scripts.graph_population.populate_studies import run as run_study
        from scripts.graph_population.populate_evidence_bodies import run as run_eb
        from scripts.graph_population.populate_relationships import run as run_rel

        run_gl(config_path)
        run_cm(config_path)
        run_rec(config_path)
        run_kq(config_path)
        run_study(config_path)
        run_eb(config_path)
        run_rel(config_path)

    elif stage == 'generate_embeddings':
        from scripts.graph_population.generate_embeddings import run
        run(config_path)

    elif stage == 'validate':
        from scripts.graph_population.validate_graph import run
        run(config_path)

    else:
        print(f"Unknown stage: {stage}")
        return False

    return True


def run(config_path: str, start_from: str = None, stop_after: str = None):
    """
    Run the full pipeline or a subset of stages.

    Args:
        config_path: Path to guideline YAML config
        start_from: Stage name to start from (inclusive)
        stop_after: Stage name to stop after (inclusive)
    """
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    # Determine stage range
    start_idx = 0
    stop_idx = len(STAGES)

    if start_from:
        if start_from not in STAGES:
            print(f"Unknown stage: {start_from}")
            print(f"Available stages: {', '.join(STAGES)}")
            return
        start_idx = STAGES.index(start_from)

    if stop_after:
        if stop_after not in STAGES:
            print(f"Unknown stage: {stop_after}")
            print(f"Available stages: {', '.join(STAGES)}")
            return
        stop_idx = STAGES.index(stop_after) + 1

    stages_to_run = STAGES[start_idx:stop_idx]

    print("=" * 60)
    print(f"HiGraph-CPG Pipeline: {config.disease_condition}")
    print(f"Config: {config_path}")
    print(f"Stages: {', '.join(stages_to_run)}")
    print("=" * 60)

    start_time = time.time()

    for stage in stages_to_run:
        stage_start = time.time()
        try:
            run_stage(stage, config_path, ctx)
            elapsed = time.time() - stage_start
            print(f"\n  Stage '{stage}' completed ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - stage_start
            print(f"\n  Stage '{stage}' FAILED after {elapsed:.1f}s: {e}")
            print(f"\n  To resume, run with: --start-from {stage}")
            return

    total_elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE ({total_elapsed:.1f}s)")
    print(f"{'='*60}")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Run the HiGraph-CPG data ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available stages:\n  " + "\n  ".join(STAGES),
    )
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--start-from', help="Stage to start from (inclusive)")
    parser.add_argument('--stop-after', help="Stage to stop after (inclusive)")
    parser.add_argument('--list-stages', action='store_true', help="List available stages and exit")
    args = parser.parse_args()

    if args.list_stages:
        print("Available pipeline stages:")
        for i, stage in enumerate(STAGES, 1):
            print(f"  {i:2d}. {stage}")
        return

    run(args.config, start_from=args.start_from, stop_after=args.stop_after)


if __name__ == "__main__":
    main()
