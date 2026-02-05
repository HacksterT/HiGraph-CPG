"""
PDF Preprocessing: Config-Driven Table Extraction

Extracts structured tables from CPG PDFs using pdfplumber. Replaces the
previous hardcoded extraction functions with a single config-driven
function that reads section definitions from the guideline YAML.
"""

import pdfplumber
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pipeline.config_loader import GuidelineConfig, SectionConfig, load_config
from scripts.pipeline.pipeline_context import PipelineContext


def extract_tables_from_page_range(
    pdf_path: str,
    start_page: int,
    end_page: int,
    table_name: str = None
) -> List[Dict[str, Any]]:
    """
    Extract all tables from a specific page range.

    Args:
        pdf_path: Path to PDF file
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed)
        table_name: Optional name for the table set

    Returns:
        List of extracted tables with metadata
    """
    tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page - 1, end_page):
            if page_num >= len(pdf.pages):
                break

            page = pdf.pages[page_num]
            page_tables = page.extract_tables()

            for table_idx, table in enumerate(page_tables):
                if table and len(table) > 1:
                    headers = table[0]
                    rows = table[1:]

                    structured_rows = []
                    for row in rows:
                        if any(cell and str(cell).strip() for cell in row):
                            row_dict = {}
                            for i, header in enumerate(headers):
                                if i < len(row):
                                    cell_value = row[i]
                                    if cell_value:
                                        cell_value = str(cell_value).strip()
                                    row_dict[header] = cell_value
                            structured_rows.append(row_dict)

                    tables.append({
                        'table_name': table_name,
                        'page': page_num + 1,
                        'table_index': table_idx,
                        'headers': headers,
                        'num_rows': len(structured_rows),
                        'data': structured_rows
                    })

    return tables


def normalize_column_names(
    rows: List[Dict[str, Any]],
    column_mapping: Dict[str, str],
    alt_column_names: Dict[str, str] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize column names in extracted rows using config-defined mapping.

    Args:
        rows: Raw extracted table rows
        column_mapping: Primary column name -> canonical name mapping
        alt_column_names: Alternative column names -> canonical name mapping

    Returns:
        Rows with normalized column names
    """
    # Build full mapping: original header -> canonical name
    full_map = dict(column_mapping)
    if alt_column_names:
        full_map.update(alt_column_names)

    normalized = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            if key in full_map:
                new_row[full_map[key]] = value
            else:
                new_row[key] = value
        normalized.append(new_row)

    return normalized


def extract_configured_tables(
    pdf_path: str,
    config: GuidelineConfig,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract all tables defined in the config from the PDF.

    Args:
        pdf_path: Path to the PDF file
        config: Loaded guideline configuration

    Returns:
        Dictionary of table_name -> {table_name, page_range, total_rows, headers, data}
    """
    tables_dict = {}

    for section_name, section_cfg in config.sections.items():
        if not section_cfg.table_name:
            continue

        table_name = section_cfg.table_name
        print(f"Extracting {table_name} (pages {section_cfg.start_page}-{section_cfg.end_page})...")

        raw_tables = extract_tables_from_page_range(
            pdf_path,
            start_page=section_cfg.start_page,
            end_page=section_cfg.end_page,
            table_name=table_name,
        )

        # Merge rows from all pages of this table
        all_rows = []
        all_headers = []
        for table in raw_tables:
            all_rows.extend(table['data'])
            if not all_headers and table['headers']:
                all_headers = table['headers']

        # Normalize column names if mapping provided
        if section_cfg.column_mapping and all_rows:
            all_rows = normalize_column_names(
                all_rows,
                section_cfg.column_mapping,
                section_cfg.alt_column_names,
            )

        print(f"  Found {len(all_rows)} rows")

        tables_dict[table_name] = {
            'table_name': table_name,
            'section': section_name,
            'page_range': f"{section_cfg.start_page}-{section_cfg.end_page}",
            'total_rows': len(all_rows),
            'headers': all_headers,
            'data': all_rows,
        }

    return tables_dict


def save_tables(tables_dict: Dict[str, Any], output_dir: str):
    """
    Save each extracted table to its own JSON file.

    Args:
        tables_dict: Dictionary of table_name -> table data
        output_dir: Directory to save JSON files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for table_name, table_data in tables_dict.items():
        file_path = output_path / f"{table_name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(table_data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {file_path}")

    # Also save a combined file for backward compatibility
    combined_path = output_path.parent / "tables.json"
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(tables_dict, f, indent=2, ensure_ascii=False)
    print(f"  Combined tables saved to {combined_path}")


def run(config_path: str):
    """Run table extraction with a guideline config."""
    config = load_config(config_path)
    ctx = PipelineContext(config)
    ctx.ensure_directories()

    pdf_path = str(ctx.pdf_path)
    if not ctx.pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        return None

    print("=" * 60)
    print(f"EXTRACTING TABLES FROM {config.disease_condition} CPG")
    print("=" * 60)

    tables_dict = extract_configured_tables(pdf_path, config)

    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    for table_name, table_data in tables_dict.items():
        expected = config.expected_counts.get(
            table_name.replace('table_5_', '').replace('table_a2_', '').replace('appendix_e_', ''),
            '?'
        )
        print(f"  {table_name}: {table_data['total_rows']} rows (expected: {expected})")

    # Save
    save_tables(tables_dict, str(ctx.tables_dir))

    print("\nTable extraction complete")
    return tables_dict


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract tables from CPG PDF")
    parser.add_argument('--config', required=True, help="Path to guideline YAML config")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
