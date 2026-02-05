"""
Pipeline Configuration Loader

Loads guideline-specific YAML configuration files, validates required fields,
and returns typed dataclasses for use throughout the pipeline.
"""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SectionConfig:
    """Configuration for a PDF section."""
    start_page: int
    end_page: int
    table_name: Optional[str] = None
    column_mapping: Optional[Dict[str, str]] = None
    alt_column_names: Optional[Dict[str, str]] = None


@dataclass
class ModuleConfig:
    """Configuration for a clinical module."""
    id_suffix: str
    name: str
    topics: List[str]
    sequence_order: int


@dataclass
class ExtractionConfig:
    """LLM extraction settings."""
    llm_provider: str = "claude"
    llm_model: str = "claude-3-5-sonnet-20241022"
    batch_size: int = 5
    max_retries: int = 3
    retry_delay: float = 2.0


@dataclass
class ConfidenceThresholds:
    """Confidence thresholds for relationship inference."""
    auto_accept: float = 0.8
    flag_for_review: float = 0.5


@dataclass
class GuidelineConfig:
    """Complete configuration for a guideline extraction pipeline."""
    # Guideline metadata
    id: str
    slug: str
    disease_condition: str
    version: str
    publication_date: str
    organization: str
    full_title: str
    status: str = "Active"
    scope_description: str = ""

    # Source PDF
    pdf_filename: str = ""
    total_pages: int = 0

    # Section page ranges
    sections: Dict[str, SectionConfig] = field(default_factory=dict)

    # Clinical modules
    modules: List[ModuleConfig] = field(default_factory=list)

    # Expected entity counts
    expected_counts: Dict[str, int] = field(default_factory=dict)

    # Extraction settings
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # Confidence thresholds
    confidence_thresholds: ConfidenceThresholds = field(default_factory=ConfidenceThresholds)


def load_config(config_path: str) -> GuidelineConfig:
    """
    Load and validate a guideline configuration from YAML.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Validated GuidelineConfig dataclass

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If required fields are missing or invalid
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        raw = yaml.safe_load(f)

    _validate_raw_config(raw)

    guideline = raw['guideline']
    source = raw.get('source', {})
    sections_raw = raw.get('sections', {})
    modules_raw = raw.get('modules', [])
    expected = raw.get('expected_counts', {})
    extraction_raw = raw.get('extraction', {})
    thresholds_raw = raw.get('confidence_thresholds', {})

    # Parse sections
    sections = {}
    for name, sec in sections_raw.items():
        sections[name] = SectionConfig(
            start_page=sec['start_page'],
            end_page=sec['end_page'],
            table_name=sec.get('table_name'),
            column_mapping=sec.get('column_mapping'),
            alt_column_names=sec.get('alt_column_names'),
        )

    # Parse modules
    modules = [
        ModuleConfig(
            id_suffix=m['id_suffix'],
            name=m['name'],
            topics=m['topics'],
            sequence_order=m['sequence_order'],
        )
        for m in modules_raw
    ]

    return GuidelineConfig(
        id=guideline['id'],
        slug=guideline['slug'],
        disease_condition=guideline['disease_condition'],
        version=guideline['version'],
        publication_date=guideline['publication_date'],
        organization=guideline['organization'],
        full_title=guideline['full_title'],
        status=guideline.get('status', 'Active'),
        scope_description=guideline.get('scope_description', ''),
        pdf_filename=source.get('pdf_filename', ''),
        total_pages=source.get('total_pages', 0),
        sections=sections,
        modules=modules,
        expected_counts=expected,
        extraction=ExtractionConfig(**extraction_raw) if extraction_raw else ExtractionConfig(),
        confidence_thresholds=ConfidenceThresholds(**thresholds_raw) if thresholds_raw else ConfidenceThresholds(),
    )


def _validate_raw_config(raw: dict):
    """Validate that required top-level fields exist."""
    if 'guideline' not in raw:
        raise ValueError("Config missing required 'guideline' section")

    guideline = raw['guideline']
    required_guideline_fields = ['id', 'slug', 'disease_condition', 'version',
                                  'publication_date', 'organization', 'full_title']
    for f in required_guideline_fields:
        if f not in guideline:
            raise ValueError(f"Config guideline section missing required field: {f}")

    if 'sections' not in raw:
        raise ValueError("Config missing required 'sections' section")

    for sec_name, sec in raw['sections'].items():
        if 'start_page' not in sec or 'end_page' not in sec:
            raise ValueError(f"Section '{sec_name}' missing start_page or end_page")


__all__ = [
    'GuidelineConfig', 'SectionConfig', 'ModuleConfig',
    'ExtractionConfig', 'ConfidenceThresholds', 'load_config',
]
