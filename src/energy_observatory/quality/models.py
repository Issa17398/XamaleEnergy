"""Modèles de données pour le contrôle qualité et la validation analytique."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CheckStatus(str, Enum):
    """Statut d'un contrôle qualité."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CheckCategory(str, Enum):
    """Catégorie de contrôle de données."""
    COMPLETENESS = "Complétude & Fraîcheur"
    REFERENTIAL_INTEGRITY = "Intégrité Référentielle"
    PHYSICAL_CONSISTENCY = "Cohérence Physique & Bilan Énergétique"
    BOUNDARY = "Bornes Plausibles & Plages de Valeurs"
    VOLUME = "Volumétrie & Typage"


@dataclass
class CheckResult:
    """Résultat unitaire d'un contrôle qualité."""
    check_id: str
    name: str
    category: CheckCategory
    status: CheckStatus
    metric_value: float
    threshold: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire sérialisable."""
        return {
            "check_id": self.check_id,
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "metric_value": round(self.metric_value, 4),
            "threshold": round(self.threshold, 4),
            "message": self.message,
            "details": self.details,
        }


@dataclass
class QualityReport:
    """Rapport global consolidé de qualité des données."""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    overall_status: CheckStatus = CheckStatus.PASS
    score_pct: float = 100.0
    total_checks: int = 0
    passed_checks: int = 0
    warn_checks: int = 0
    failed_checks: int = 0
    duration_seconds: float = 0.0
    checks: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le rapport en dictionnaire JSON."""
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "score_pct": round(self.score_pct, 2),
            "summary": {
                "total": self.total_checks,
                "passed": self.passed_checks,
                "warn": self.warn_checks,
                "failed": self.failed_checks,
                "duration_seconds": round(self.duration_seconds, 2),
            },
            "checks": [c.to_dict() for c in self.checks],
        }
