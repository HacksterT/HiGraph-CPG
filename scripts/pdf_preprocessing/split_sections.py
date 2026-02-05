"""
PDF Preprocessing: Split PDF into Sections

Splits a CPG PDF into section-specific PDFs using page ranges from
the guideline YAML config. Uses PyMuPDF for fast, lossless splitting.
"""

import fitz  # PyMuPDF
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext


def split_pdf_by_sections(pdf_path: str, sections: dict, output_dir: str) -> dict:
    """
    Split a PDF into separate files for each configured section.

    Args:
        pdf_path: Path to source PDF
        sections: Dict of section_name -> SectionConfig
        output_dir: Directory to write section PDFs

    Returns:
        Dict of section_name -> output_path for successfully split sections
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    results = {}

    for section_name, section_cfg in sections.items():
        start = section_cfg.start_page - 1  # fitz is 0-indexed
        end = min(section_cfg.end_page, total_pages)  # inclusive in config, exclusive in fitz

        if start >= total_pages:
            print(f"  WARNING: {section_name} start page {section_cfg.start_page} exceeds PDF length ({total_pages})")
            continue

        section_doc = fitz.open()
        section_doc.insert_pdf(doc, from_page=start, to_page=end - 1)

        out_file = output_path / f"{section_name}.pdf"
        section_doc.save(str(out_file))
        section_doc.close()

        page_count = end - start
        print(f"  {section_name}: pages {section_cfg.start_page}-{section_cfg.end_page} -> {out_file.name} ({page_count} pages)")
        results[section_name] = str(out_file)

    doc.close()
    return results


def run(config_path: str):
    """Run section splitting with a guideline config."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    pdf_path = str(ctx.pdf_path)
    if not ctx.pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return None

    print(f"Splitting {config.pdf_filename} into sections...")
    results = split_pdf_by_sections(pdf_path, config.sections, str(ctx.sections_dir))

    print(f"\nSplit into {len(results)} section PDFs")
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Split CPG PDF into sections")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
