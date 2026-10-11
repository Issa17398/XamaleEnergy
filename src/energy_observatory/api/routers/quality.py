"""Routeur pour les audits et rapports de qualité des données (Couche Gold)."""

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query

from config.settings import settings
from src.energy_observatory.api.schemas import QualityReportResponse, QualityRuleDetail
from src.energy_observatory.quality.validator import DataQualityValidator

router = APIRouter(prefix="/quality", tags=["Qualité des Données & Audit"])


@router.get(
    "/report",
    response_model=QualityReportResponse,
    summary="Dernier rapport d'audit qualité des données",
    description="Retourne le bilan des 10 règles de validation physique, mathématique et d'intégrité référentielle.",
)
def get_quality_report(
    refresh: bool = Query(default=False, description="Forcer une nouvelle exécution des 10 règles en direct")
) -> QualityReportResponse:
    """Charge le rapport JSON existant ou exécute le validateur si demandé."""
    reports_dir = settings.DATA_REPORTS_DIR
    json_reports = sorted(reports_dir.glob("data_quality_report_*.json"), reverse=True)

    if not refresh and json_reports:
        latest_file = json_reports[0]
        try:
            data = json.loads(latest_file.read_text(encoding="utf-8"))
            summary = data.get("summary", {})
            rules = [
                QualityRuleDetail(
                    code=c.get("check_id", ""),
                    category=c.get("category", ""),
                    description=c.get("name", ""),
                    passed=(c.get("status") == "PASS"),
                    severity=c.get("status", "PASS"),
                    measured_value=c.get("metric_value"),
                    details=c.get("message", ""),
                )
                for c in data.get("checks", [])
            ]
            return QualityReportResponse(
                generated_at=data.get("timestamp", ""),
                global_score_pct=float(data.get("score_pct", 100.0)),
                total_rules=int(summary.get("total", len(rules))),
                passed_rules=int(summary.get("passed", len(rules))),
                failed_rules=int(summary.get("failed", 0)),
                status=data.get("overall_status", "PASS"),
                rules=rules,
            )
        except Exception:
            # En cas de problème de lecture, on recalcule en direct
            pass

    # Exécution en direct via le validateur
    validator = DataQualityValidator()
    report = validator.run_all_checks()

    rules = [
        QualityRuleDetail(
            code=c.check_id,
            category=c.category.value,
            description=c.name,
            passed=(c.status.value == "PASS"),
            severity=c.status.value,
            measured_value=c.metric_value,
            details=c.message,
        )
        for c in report.checks
    ]

    return QualityReportResponse(
        generated_at=report.timestamp,
        global_score_pct=round(report.score_pct, 2),
        total_rules=report.total_checks,
        passed_rules=report.passed_checks,
        failed_rules=report.failed_checks,
        status=report.overall_status.value,
        rules=rules,
    )
