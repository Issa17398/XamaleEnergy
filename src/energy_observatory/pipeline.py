"""Orchestrateur central du pipeline de données (Architecture Medallion End-to-End).

Ce module unifie et automatise les 4 étapes du cycle de vie de la donnée :
1. BRONZE   : Ingestion résiliente des flux bruts (RTE, Enedis, Banque Mondiale)
2. SILVER   : Nettoyage, typage strict, gestion des auxiliaires et rejets
3. GOLD     : Chargement haute performance dans le modèle en étoile PostgreSQL
4. QUALITY  : Audit automatisé des 10 règles de conformité et export des rapports
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import sys
import time
from typing import Any, Dict, List, Optional

from config.settings import settings
from src.energy_observatory.ingestion.enedis import ingest_enedis_registre_bronze
from src.energy_observatory.ingestion.rte import ingest_rte_national_bronze
from src.energy_observatory.ingestion.world_bank import ingest_world_bank_bronze
from src.energy_observatory.quality.models import CheckStatus
from src.energy_observatory.quality.reporter import export_quality_report
from src.energy_observatory.quality.validator import DataQualityValidator
from src.energy_observatory.storage.db import check_connection, get_engine
from src.energy_observatory.storage.load_gold import load_silver_to_gold
from src.energy_observatory.transformation.run_all import run_all_silver_transformations
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class StageResult:
    """Résultat d'exécution d'une étape du pipeline."""

    stage_name: str
    status: str  # "SUCCESS", "SKIPPED", "FAILED"
    duration_seconds: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PipelineReport:
    """Bilan global d'exécution du pipeline end-to-end."""

    status: str
    total_duration_seconds: float
    stages: List[StageResult] = field(default_factory=list)
    quality_score: Optional[float] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def run_bronze_stage(force_download: bool = False) -> StageResult:
    """Étape 1 : Ingestion des 3 sources de données brutes vers la couche Bronze.

    Args:
        force_download: Force le re-téléchargement si True.

    Returns:
        StageResult: Rapport d'exécution de l'étape Bronze.
    """
    logger.info(">>> [Pipeline] Étape 1/4 : Ingestion Bronze...")
    t0 = time.time()
    try:
        rte_res = ingest_rte_national_bronze(force_download=force_download)
        enedis_res = ingest_enedis_registre_bronze(force_download=force_download)
        wb_res = ingest_world_bank_bronze(force_download=force_download)

        metrics = {
            "rte_rows": rte_res.row_count,
            "rte_status": rte_res.status,
            "enedis_rows": enedis_res.row_count,
            "enedis_status": enedis_res.status,
            "worldbank_rows": wb_res.total_observations,
            "worldbank_status": wb_res.status,
        }
        duration = round(time.time() - t0, 2)
        logger.info(f">>> [Pipeline] Étape Bronze terminée en {duration} s.")
        return StageResult(
            stage_name="1. BRONZE_INGESTION",
            status="SUCCESS",
            duration_seconds=duration,
            metrics=metrics,
        )
    except Exception as e:
        duration = round(time.time() - t0, 2)
        logger.error(f">>> [Pipeline] Échec étape Bronze : {e}", exc_info=True)
        return StageResult(
            stage_name="1. BRONZE_INGESTION",
            status="FAILED",
            duration_seconds=duration,
            error=str(e),
        )


def run_silver_stage() -> StageResult:
    """Étape 2 : Nettoyage, typage strict et export Parquet vers la couche Silver.

    Returns:
        StageResult: Rapport d'exécution de l'étape Silver.
    """
    logger.info(">>> [Pipeline] Étape 2/4 : Transformation Silver...")
    t0 = time.time()
    try:
        silver_results = run_all_silver_transformations()
        metrics = {
            res.source_name: {
                "valid_rows": res.valid_output_rows,
                "rejected_rows": res.rejected_rows,
                "duration": res.duration_seconds,
            }
            for res in silver_results
        }
        duration = round(time.time() - t0, 2)
        logger.info(f">>> [Pipeline] Étape Silver terminée en {duration} s.")
        return StageResult(
            stage_name="2. SILVER_TRANSFORMATION",
            status="SUCCESS",
            duration_seconds=duration,
            metrics=metrics,
        )
    except Exception as e:
        duration = round(time.time() - t0, 2)
        logger.error(f">>> [Pipeline] Échec étape Silver : {e}", exc_info=True)
        return StageResult(
            stage_name="2. SILVER_TRANSFORMATION",
            status="FAILED",
            duration_seconds=duration,
            error=str(e),
        )


def run_gold_stage() -> StageResult:
    """Étape 3 : Chargement haute performance vers le modèle en étoile PostgreSQL.

    Returns:
        StageResult: Rapport d'exécution de l'étape Gold.
    """
    logger.info(">>> [Pipeline] Étape 3/4 : Chargement Gold (PostgreSQL)...")
    t0 = time.time()
    try:
        # Vérification préalable de la base
        if not check_connection():
            raise ConnectionError(
                f"Impossible de se connecter à PostgreSQL sur {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}. "
                "Assurez-vous que Docker est démarré ('docker compose up -d')."
            )

        gold_report = load_silver_to_gold()
        if gold_report.status != "SUCCESS":
            raise RuntimeError(f"Échec du chargement Gold : {gold_report.errors}")

        metrics = {
            "dim_temps": gold_report.rows_dim_temps,
            "dim_geographie": gold_report.rows_dim_geographie,
            "fact_electricite": gold_report.rows_fact_electricite,
            "fact_registre": gold_report.rows_fact_registre,
            "fact_worldbank": gold_report.rows_fact_worldbank,
        }
        duration = round(time.time() - t0, 2)
        logger.info(f">>> [Pipeline] Étape Gold terminée en {duration} s.")
        return StageResult(
            stage_name="3. GOLD_LOADING",
            status="SUCCESS",
            duration_seconds=duration,
            metrics=metrics,
        )
    except Exception as e:
        duration = round(time.time() - t0, 2)
        logger.error(f">>> [Pipeline] Échec étape Gold : {e}", exc_info=True)
        return StageResult(
            stage_name="3. GOLD_LOADING",
            status="FAILED",
            duration_seconds=duration,
            error=str(e),
        )


def run_quality_stage() -> StageResult:
    """Étape 4 : Audit de qualité des données et export des rapports.

    Returns:
        StageResult: Rapport d'exécution de l'étape Qualité.
    """
    logger.info(">>> [Pipeline] Étape 4/4 : Contrôle Qualité & Audit...")
    t0 = time.time()
    try:
        validator = DataQualityValidator()
        report = validator.run_all_checks()
        json_path, md_path = export_quality_report(report)

        metrics = {
            "score_pct": report.score_pct,
            "passed_checks": report.passed_checks,
            "total_checks": report.total_checks,
            "report_md": str(md_path),
            "report_json": str(json_path),
        }
        duration = round(time.time() - t0, 2)
        status = "SUCCESS" if report.overall_status in (CheckStatus.PASS, CheckStatus.WARN) else "FAILED"
        logger.info(
            f">>> [Pipeline] Étape Qualité terminée en {duration} s (Score: {report.score_pct:.1f}%)."
        )
        return StageResult(
            stage_name="4. QUALITY_VALIDATION",
            status=status,
            duration_seconds=duration,
            metrics=metrics,
        )
    except Exception as e:
        duration = round(time.time() - t0, 2)
        logger.error(f">>> [Pipeline] Échec étape Qualité : {e}", exc_info=True)
        return StageResult(
            stage_name="4. QUALITY_VALIDATION",
            status="FAILED",
            duration_seconds=duration,
            error=str(e),
        )


def run_full_pipeline(
    force_download: bool = False,
    selected_stage: str = "all",
) -> PipelineReport:
    """Exécute le pipeline selon les étapes sélectionnées.

    Args:
        force_download: Force le téléchargement des fichiers bruts si True.
        selected_stage: 'all', 'bronze', 'silver', 'gold', ou 'quality'.

    Returns:
        PipelineReport: Bilan d'exécution consolidé.
    """
    total_start = time.time()
    stages_to_run = {
        "all": ["bronze", "silver", "gold", "quality"],
        "bronze": ["bronze"],
        "silver": ["silver"],
        "gold": ["gold"],
        "quality": ["quality"],
    }.get(selected_stage.lower(), ["bronze", "silver", "gold", "quality"])

    logger.info("==================================================================")
    logger.info(f"DÉMARRAGE DU PIPELINE COMPLET — Étapes : {', '.join(stages_to_run)}")
    logger.info("==================================================================")

    stage_results: List[StageResult] = []
    overall_status = "SUCCESS"
    quality_score: Optional[float] = None

    # Exécution ordonnée
    for stg in stages_to_run:
        if stg == "bronze":
            res = run_bronze_stage(force_download=force_download)
        elif stg == "silver":
            res = run_silver_stage()
        elif stg == "gold":
            res = run_gold_stage()
        elif stg == "quality":
            res = run_quality_stage()
            if "score_pct" in res.metrics:
                quality_score = res.metrics["score_pct"]
        else:
            continue

        stage_results.append(res)
        if res.status == "FAILED":
            overall_status = "FAILED"
            logger.error(f"Arrêt prématuré du pipeline suite à l'échec de : {res.stage_name}")
            break

    total_duration = round(time.time() - total_start, 2)
    return PipelineReport(
        status=overall_status,
        total_duration_seconds=total_duration,
        stages=stage_results,
        quality_score=quality_score,
    )


def print_pipeline_summary(report: PipelineReport) -> None:
    """Affiche une synthèse claire et lisible du pipeline dans la console."""
    print("\n" + "=" * 70)
    print("BILAN D'EXÉCUTION DU PIPELINE DE DONNÉES (END-TO-END)")
    print("=" * 70)
    print(f"Statut Global        : {report.status}")
    print(f"Durée Totale         : {report.total_duration_seconds} s")
    if report.quality_score is not None:
        print(f"Score Qualité Final  : {report.quality_score:.2f}%")
    print("-" * 70)
    print(f"{'Étape':<26} | {'Statut':<9} | {'Durée':<8} | Détails")
    print("-" * 70)

    for stg in report.stages:
        tag = "[OK]  " if stg.status == "SUCCESS" else "[FAIL]"
        details_str = ""
        if stg.metrics:
            if "rte_rows" in stg.metrics:
                details_str = f"RTE: {stg.metrics['rte_rows']:,} lig., Enedis: {stg.metrics['enedis_rows']:,} lig."
            elif "RTE_ECO2MIX_NATIONAL" in stg.metrics:
                details_str = "Parquet générés (RTE 257k, Enedis 125k, WB 66)"
            elif "fact_electricite" in stg.metrics:
                details_str = f"PostgreSQL: {stg.metrics['fact_electricite']:,} faits, {stg.metrics['dim_geographie']:,} communes"
            elif "score_pct" in stg.metrics:
                details_str = f"Score: {stg.metrics['score_pct']:.1f}% ({stg.metrics['passed_checks']}/{stg.metrics['total_checks']} règles)"
        if stg.error:
            details_str = f"ERREUR: {stg.error}"

        print(f"{stg.stage_name:<26} | {tag:<9} | {stg.duration_seconds:>5.2f} s | {details_str}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Observatoire Énergie — Orchestrateur du Pipeline Complet"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "bronze", "silver", "gold", "quality"],
        default="all",
        help="Étape spécifique à exécuter (défaut : all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force le re-téléchargement des fichiers Bronze",
    )
    args = parser.parse_args()

    pipeline_report = run_full_pipeline(
        force_download=args.force,
        selected_stage=args.stage,
    )
    print_pipeline_summary(pipeline_report)

    if pipeline_report.status != "SUCCESS":
        sys.exit(1)
