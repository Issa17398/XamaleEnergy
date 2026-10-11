"""Module de contrôle qualité et de gouvernance des données (Couche Gold)."""

from src.energy_observatory.quality.models import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    QualityReport,
)
from src.energy_observatory.quality.reporter import (
    export_quality_report,
    generate_markdown_report,
)
def __getattr__(name: str):
    if name == "DataQualityValidator":
        from src.energy_observatory.quality.validator import DataQualityValidator
        return DataQualityValidator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CheckCategory",
    "CheckResult",
    "CheckStatus",
    "QualityReport",
    "export_quality_report",
    "generate_markdown_report",
    "DataQualityValidator",
]
