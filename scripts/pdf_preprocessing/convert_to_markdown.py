"""
PDF Preprocessing: Convert Section PDFs to Markdown

Converts split section PDFs into markdown format using marker-pdf for
high-quality text extraction that preserves structure. Falls back to
PyMuPDF text extraction if marker-pdf is unavailable or fails.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import load_config
from scripts.pipeline.pipeline_context import PipelineContext

# Try importing marker-pdf
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False


def convert_with_marker(pdf_path: str, output_path: str) -> str:
    """
    Convert a PDF to markdown using marker-pdf.

    Args:
        pdf_path: Path to input PDF
        output_path: Path to write markdown output

    Returns:
        The markdown text
    """
    if not MARKER_AVAILABLE:
        raise ImportError("marker-pdf not installed. Run: pip install marker-pdf")

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(pdf_path)
    markdown_text = rendered.markdown

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    return markdown_text


def convert_with_pymupdf(pdf_path: str, output_path: str) -> str:
    """
    Fallback: extract text from PDF using PyMuPDF.

    Less structured than marker-pdf but always available.

    Args:
        pdf_path: Path to input PDF
        output_path: Path to write markdown output

    Returns:
        The extracted text
    """
    import fitz

    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text.strip():
            text_parts.append(f"<!-- Page {page_num + 1} -->\n\n{text}")

    doc.close()

    markdown_text = "\n\n---\n\n".join(text_parts)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    return markdown_text


def convert_section(pdf_path: str, output_path: str, use_marker: bool = True) -> str:
    """
    Convert a section PDF to markdown, with fallback.

    Args:
        pdf_path: Path to section PDF
        output_path: Path for markdown output
        use_marker: Try marker-pdf first (falls back to PyMuPDF)

    Returns:
        The markdown text
    """
    if use_marker and MARKER_AVAILABLE:
        try:
            return convert_with_marker(pdf_path, output_path)
        except Exception as e:
            print(f"  marker-pdf failed ({e}), falling back to PyMuPDF")

    return convert_with_pymupdf(pdf_path, output_path)


def run(config_path: str, use_marker: bool = True):
    """Convert all section PDFs to markdown."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    sections_dir = ctx.sections_dir
    section_pdfs = list(sections_dir.glob("*.pdf"))

    if not section_pdfs:
        print("No section PDFs found. Run split_sections.py first.")
        return {}

    print(f"Converting {len(section_pdfs)} section PDFs to markdown...")
    if not MARKER_AVAILABLE:
        print("  Note: marker-pdf not available, using PyMuPDF fallback")

    results = {}
    for pdf_file in sorted(section_pdfs):
        section_name = pdf_file.stem
        md_path = ctx.section_md_path(section_name)

        print(f"  Converting {section_name}...")
        try:
            text = convert_section(str(pdf_file), str(md_path), use_marker=use_marker)
            results[section_name] = {
                'path': str(md_path),
                'length': len(text),
            }
        except Exception as e:
            print(f"  ERROR converting {section_name}: {e}")
            results[section_name] = {'error': str(e)}

    print(f"\nConverted {sum(1 for v in results.values() if 'path' in v)}/{len(section_pdfs)} sections")
    return results


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Convert section PDFs to markdown")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    parser.add_argument('--no-marker', action='store_true', help="Skip marker-pdf, use PyMuPDF only")
    args = parser.parse_args()
    run(args.config, use_marker=not args.no_marker)


if __name__ == "__main__":
    main()
