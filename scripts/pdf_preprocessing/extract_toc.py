"""
PDF Preprocessing: Extract Table of Contents and Create Document Map

Extracts the table of contents from a CPG PDF and creates a document map
with section boundaries for targeted extraction. Config-driven: reads page
ranges and section keywords from the guideline YAML config.
"""

import fitz  # PyMuPDF
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import GuidelineConfig, load_config
from scripts.pipeline.pipeline_context import PipelineContext


def extract_toc(pdf_path: str) -> List[Tuple[int, str, int]]:
    """
    Extract table of contents from PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of (level, title, page) tuples
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # Returns [(level, title, page), ...]
    doc.close()
    return toc


def create_document_map(toc: List[Tuple[int, str, int]], config: GuidelineConfig) -> Dict[str, dict]:
    """
    Create a document map from TOC entries and config-defined sections.

    Uses the config's section definitions as the authoritative page ranges,
    and supplements with any additional sections discovered in the TOC.

    Args:
        toc: Table of contents from extract_toc
        config: Loaded guideline configuration

    Returns:
        Dictionary mapping section names to {start_page, end_page, num_pages, source}
    """
    document_map = {}

    # Add all config-defined sections (authoritative)
    for section_name, section_cfg in config.sections.items():
        document_map[section_name] = {
            'start_page': section_cfg.start_page,
            'end_page': section_cfg.end_page,
            'num_pages': section_cfg.end_page - section_cfg.start_page + 1,
            'source': 'config',
        }

    # Add TOC entries as supplementary context
    toc_entries = []
    for level, title, page in toc:
        end_page = config.total_pages  # default
        toc_entries.append({
            'level': level,
            'title': title,
            'start_page': page,
        })

    # Compute end pages from sequential TOC entries
    for i, entry in enumerate(toc_entries):
        if i + 1 < len(toc_entries):
            entry['end_page'] = toc_entries[i + 1]['start_page'] - 1
        else:
            entry['end_page'] = config.total_pages

    document_map['_toc_entries'] = toc_entries

    return document_map


def save_document_map(document_map: dict, output_path: str) -> dict:
    """
    Save document map to JSON file.

    Args:
        document_map: Section boundaries dictionary
        output_path: Path to save JSON file

    Returns:
        The saved map data
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(document_map, f, indent=2)

    print(f"Document map saved to {output_path}")
    return document_map


def run(config_path: str):
    """Run TOC extraction with a guideline config."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    pdf_path = str(ctx.pdf_path)
    output_path = str(ctx.document_map_path)

    print(f"Extracting TOC from {pdf_path}...")
    if not ctx.pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        print("Check that the PDF exists in one of:")
        print(f"  {ctx.source_dir}")
        print(f"  {ctx.root / 'docs' / 'source-guidelines'}")
        return None

    toc = extract_toc(pdf_path)
    print(f"Found {len(toc)} TOC entries")

    print("Creating document map...")
    document_map = create_document_map(toc, config)

    # Print config-defined sections
    config_sections = {k: v for k, v in document_map.items() if k != '_toc_entries'}
    print(f"Config-defined sections ({len(config_sections)}):")
    for section, info in config_sections.items():
        print(f"  {section}: pages {info['start_page']}-{info['end_page']} ({info['num_pages']} pages)")

    print(f"\nSaving document map...")
    save_document_map(document_map, output_path)

    print("\nDocument map created successfully")
    return document_map


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract TOC and create document map")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
