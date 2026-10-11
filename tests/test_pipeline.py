"""Tests unitaires et d'intégration pour l'orchestrateur du pipeline complet."""

from unittest.mock import MagicMock, patch

import pytest

from src.energy_observatory.pipeline import (
    StageResult,
    PipelineReport,
    run_bronze_stage,
    run_silver_stage,
    run_gold_stage,
    run_quality_stage,
    run_full_pipeline,
)
from src.energy_observatory.transformation.cleaning import TransformationResult


def test_run_bronze_stage_mock():
    """Vérifie l'exécution nominale de l'étape Bronze avec mocks."""
    mock_rte = MagicMock(row_count=500000, status="SUCCESS")
    mock_enedis = MagicMock(row_count=125000, status="SUCCESS")
    mock_wb = MagicMock(total_observations=66, status="SUCCESS")

    with patch("src.energy_observatory.pipeline.ingest_rte_national_bronze", return_value=mock_rte), \
         patch("src.energy_observatory.pipeline.ingest_enedis_registre_bronze", return_value=mock_enedis), \
         patch("src.energy_observatory.pipeline.ingest_world_bank_bronze", return_value=mock_wb):

        res = run_bronze_stage(force_download=False)

        assert res.status == "SUCCESS"
        assert res.stage_name == "1. BRONZE_INGESTION"
        assert res.metrics["rte_rows"] == 500000
        assert res.metrics["enedis_rows"] == 125000
        assert res.metrics["worldbank_rows"] == 66


def test_run_silver_stage_mock():
    """Vérifie l'exécution nominale de l'étape Silver avec mocks."""
    mock_res = TransformationResult(
        status="SUCCESS",
        source_name="TEST_SOURCE",
        bronze_input_path="mock/path.csv",
        silver_output_path="mock/path.parquet",
        rejected_output_path=None,
        total_input_rows=1000,
        valid_output_rows=990,
        rejected_rows=10,
        columns=["a", "b"],
        duration_seconds=1.2,
    )

    with patch("src.energy_observatory.pipeline.run_all_silver_transformations", return_value=[mock_res]):
        res = run_silver_stage()

        assert res.status == "SUCCESS"
        assert res.stage_name == "2. SILVER_TRANSFORMATION"
        assert "TEST_SOURCE" in res.metrics
        assert res.metrics["TEST_SOURCE"]["valid_rows"] == 990


def test_run_gold_stage_db_unreachable():
    """Vérifie la gestion d'erreur propre lorsque PostgreSQL est inaccessible."""
    with patch("src.energy_observatory.pipeline.check_connection", return_value=False):
        res = run_gold_stage()

        assert res.status == "FAILED"
        assert "Impossible de se connecter à PostgreSQL" in res.error


def test_run_full_pipeline_selective_stage():
    """Valide l'exécution ciblée d'une seule étape."""
    mock_stage = StageResult(
        stage_name="4. QUALITY_VALIDATION",
        status="SUCCESS",
        duration_seconds=0.5,
        metrics={"score_pct": 100.0, "passed_checks": 10, "total_checks": 10},
    )

    with patch("src.energy_observatory.pipeline.run_quality_stage", return_value=mock_stage):
        report = run_full_pipeline(selected_stage="quality")

        assert report.status == "SUCCESS"
        assert len(report.stages) == 1
        assert report.stages[0].stage_name == "4. QUALITY_VALIDATION"
        assert report.quality_score == 100.0


def test_run_full_pipeline_early_exit_on_failure():
    """Vérifie que l'échec d'une étape interrompt immédiatement le pipeline."""
    mock_failed_bronze = StageResult(
        stage_name="1. BRONZE_INGESTION",
        status="FAILED",
        duration_seconds=0.2,
        error="Network Timeout",
    )

    with patch("src.energy_observatory.pipeline.run_bronze_stage", return_value=mock_failed_bronze), \
         patch("src.energy_observatory.pipeline.run_silver_stage") as mock_silver:

        report = run_full_pipeline(selected_stage="all")

        assert report.status == "FAILED"
        assert len(report.stages) == 1
        mock_silver.assert_not_called()
