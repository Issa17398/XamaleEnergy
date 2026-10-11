"""Tests unitaires et d'intégration pour le module de contrôle qualité des données."""

from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
from src.energy_observatory.quality.validator import DataQualityValidator
from src.energy_observatory.storage.db import check_connection


def test_models_serialization():
    """Vérifie la sérialisation des modèles CheckResult et QualityReport."""
    result = CheckResult(
        check_id="TEST-01",
        name="Test de complétude",
        category=CheckCategory.COMPLETENESS,
        status=CheckStatus.PASS,
        metric_value=100.0,
        threshold=95.0,
        message="Tout est conforme",
        details={"count": 100},
    )

    d = result.to_dict()
    assert d["check_id"] == "TEST-01"
    assert d["status"] == "PASS"
    assert d["metric_value"] == 100.0

    report = QualityReport(
        overall_status=CheckStatus.PASS,
        score_pct=100.0,
        total_checks=1,
        passed_checks=1,
        warn_checks=0,
        failed_checks=0,
        checks=[result],
    )

    rep_dict = report.to_dict()
    assert rep_dict["overall_status"] == "PASS"
    assert rep_dict["score_pct"] == 100.0
    assert len(rep_dict["checks"]) == 1


def test_markdown_report_generation():
    """Valide la mise en forme du rapport d'audit en Markdown."""
    result = CheckResult(
        check_id="REF-01",
        name="Intégrité Référentielle",
        category=CheckCategory.REFERENTIAL_INTEGRITY,
        status=CheckStatus.PASS,
        metric_value=0.0,
        threshold=0.0,
        message="Aucun orphelin",
    )
    report = QualityReport(
        overall_status=CheckStatus.PASS,
        score_pct=100.0,
        total_checks=1,
        passed_checks=1,
        checks=[result],
    )

    md = generate_markdown_report(report)
    assert "# Rapport d'Audit & Contrôle Qualité" in md
    assert "100.00%" in md
    assert "REF-01" in md
    assert "Intégrité Référentielle" in md


def test_export_quality_report(tmp_path):
    """Vérifie l'écriture des fichiers JSON et Markdown par le reporter."""
    report = QualityReport(
        overall_status=CheckStatus.PASS,
        score_pct=100.0,
        total_checks=0,
        passed_checks=0,
    )

    json_p, md_p = export_quality_report(report, output_dir=tmp_path)

    assert json_p.exists()
    assert md_p.exists()
    assert json_p.suffix == ".json"
    assert md_p.suffix == ".md"

    with open(json_p, mode="r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["score_pct"] == 100.0


def test_validator_live_db_checks():
    """Exécute les contrôles de qualité sur la base PostgreSQL si connectée."""
    if not check_connection():
        pytest.skip("Base PostgreSQL non disponible pour ce test d'intégration.")

    validator = DataQualityValidator()
    report = validator.run_all_checks()

    assert report.total_checks == 10
    assert report.score_pct >= 95.0
    assert report.failed_checks == 0
    assert report.overall_status in (CheckStatus.PASS, CheckStatus.WARN)
