"""
Pipeline Context

Resolves all file paths from a GuidelineConfig, providing a single object
that any pipeline stage can use to find its inputs and outputs.
"""

from pathlib import Path
from typing import Optional

from .config_loader import GuidelineConfig


class PipelineContext:
    """Resolves all file system paths for a guideline pipeline run."""

    def __init__(self, config: GuidelineConfig, project_root: Optional[str] = None):
        """
        Args:
            config: Loaded guideline configuration
            project_root: Project root directory. Defaults to cwd.
        """
        self.config = config
        self.root = Path(project_root) if project_root else Path.cwd()
        self.slug = config.slug

        # Base data directory for this guideline
        self.guideline_dir = self.root / "data" / "guidelines" / self.slug

        # Source
        self.source_dir = self.guideline_dir / "source"
        self.pdf_path = self._resolve_pdf_path()

        # Preprocessed
        self.preprocessed_dir = self.guideline_dir / "preprocessed"
        self.tables_dir = self.preprocessed_dir / "tables"
        self.sections_dir = self.preprocessed_dir / "sections"
        self.document_map_path = self.preprocessed_dir / "document_map.json"

        # Extracted
        self.extracted_dir = self.guideline_dir / "extracted"
        self.guideline_json = self.extracted_dir / "guideline.json"
        self.clinical_modules_json = self.extracted_dir / "clinical_modules.json"
        self.recommendations_json = self.extracted_dir / "recommendations.json"
        self.key_questions_json = self.extracted_dir / "key_questions.json"
        self.studies_json = self.extracted_dir / "studies.json"
        self.evidence_bodies_json = self.extracted_dir / "evidence_bodies.json"
        self.relationships_json = self.extracted_dir / "relationships.json"

        # Checkpoints
        self.checkpoints_dir = self.guideline_dir / "checkpoints"

        # Manual review
        self.manual_review_dir = self.guideline_dir / "manual_review"

        # Validation
        self.validation_dir = self.guideline_dir / "validation"

        # Shared (cross-guideline)
        self.shared_dir = self.root / "data" / "shared"
        self.pubmed_cache_dir = self.shared_dir / "pubmed_cache"

    def _resolve_pdf_path(self) -> Path:
        """Resolve the source PDF path, checking multiple locations."""
        # Check guideline-specific source directory
        local_pdf = self.guideline_dir / "source" / self.config.pdf_filename
        if local_pdf.exists():
            return local_pdf

        # Check docs/source-guidelines (original location)
        docs_pdf = self.root / "docs" / "source-guidelines" / self.config.pdf_filename
        if docs_pdf.exists():
            return docs_pdf

        # Check legacy data/source location
        legacy_pdf = self.root / "data" / "source" / self.config.pdf_filename
        if legacy_pdf.exists():
            return legacy_pdf

        # Return the expected location even if file doesn't exist yet
        return local_pdf

    def ensure_directories(self):
        """Create all output directories if they don't exist."""
        for d in [
            self.source_dir,
            self.preprocessed_dir,
            self.tables_dir,
            self.sections_dir,
            self.extracted_dir,
            self.checkpoints_dir,
            self.manual_review_dir,
            self.validation_dir,
            self.pubmed_cache_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def table_path(self, table_name: str) -> Path:
        """Path for a specific extracted table JSON."""
        return self.tables_dir / f"{table_name}.json"

    def section_pdf_path(self, section_name: str) -> Path:
        """Path for a split section PDF."""
        return self.sections_dir / f"{section_name}.pdf"

    def section_md_path(self, section_name: str) -> Path:
        """Path for a section's markdown conversion."""
        return self.sections_dir / f"{section_name}.md"

    def checkpoint_path(self, task_name: str) -> Path:
        """Directory for checkpoints of a given task."""
        return self.checkpoints_dir / task_name

    def validation_report_path(self, entity_type: str) -> Path:
        """Path for a validation report."""
        return self.validation_dir / f"validate_{entity_type}.json"

    def entity_id(self, prefix: str, number: int) -> str:
        """
        Generate a deterministic entity ID.

        Args:
            prefix: Entity type prefix (REC, KQ, STUDY, EVB, MOD, GL)
            number: Entity number

        Returns:
            ID like CPG_DM_2023_REC_001
        """
        return f"{self.config.id}_{prefix}_{number:03d}"

    def module_id(self, id_suffix: str) -> str:
        """Generate a module ID from its config suffix."""
        return f"{self.config.id}_{id_suffix}"

    def __repr__(self):
        return f"PipelineContext(slug={self.slug!r}, root={self.root})"


__all__ = ['PipelineContext']
