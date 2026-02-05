"""
Extract Guideline and Clinical Module Metadata

Generates guideline.json and clinical_modules.json directly from the
YAML config — no LLM needed. These structural entities come from the
config file, not from PDF extraction.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def generate_guideline_json(ctx: PipelineContext) -> dict:
    """
    Generate guideline entity from config metadata.

    Args:
        ctx: Pipeline context

    Returns:
        Guideline entity dict
    """
    config = ctx.config
    guideline = {
        'guideline_id': config.id,
        'disease_condition': config.disease_condition,
        'version': config.version,
        'publication_date': config.publication_date,
        'organization': config.organization,
        'full_title': config.full_title,
        'status': config.status,
        'scope_description': config.scope_description,
    }
    return guideline


def generate_clinical_modules_json(ctx: PipelineContext) -> list:
    """
    Generate clinical module entities from config module definitions.

    Args:
        ctx: Pipeline context

    Returns:
        List of clinical module entity dicts
    """
    modules = []
    for mod in ctx.config.modules:
        module = {
            'module_id': ctx.module_id(mod.id_suffix),
            'module_name': mod.name,
            'description': f"Clinical module covering {mod.name} topics",
            'guideline_id': ctx.config.id,
            'sequence_order': mod.sequence_order,
            'topics': mod.topics,
        }
        modules.append(module)

    return modules


def run(config_path: str):
    """Generate guideline and clinical module metadata."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    print("Generating guideline metadata...")
    guideline = generate_guideline_json(ctx)

    with open(ctx.guideline_json, 'w') as f:
        json.dump(guideline, f, indent=2)
    print(f"  Saved {ctx.guideline_json}")

    print("Generating clinical modules...")
    modules = generate_clinical_modules_json(ctx)

    with open(ctx.clinical_modules_json, 'w') as f:
        json.dump(modules, f, indent=2)
    print(f"  Saved {ctx.clinical_modules_json} ({len(modules)} modules)")

    print("\nMetadata generation complete")
    return guideline, modules


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate guideline metadata from config")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
