"""Script d'orchestration pour exécuter toutes les transformations Silver."""

import time
from typing import List

from src.energy_observatory.transformation.cleaning import TransformationResult
from src.energy_observatory.transformation.enedis_transform import (
    transform_enedis_registre_bronze_to_silver,
)
from src.energy_observatory.transformation.rte_transform import (
    transform_rte_national_bronze_to_silver,
)
from src.energy_observatory.transformation.world_bank_transform import (
    transform_world_bank_bronze_to_silver,
)
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


def run_all_silver_transformations() -> List[TransformationResult]:
    """Exécute séquentiellement toutes les transformations Bronze vers Silver.

    Returns:
        List[TransformationResult]: Liste des résultats pour chaque source.
    """
    logger.info("==================================================")
    logger.info("DÉBUT DU PIPELINE DE TRANSFORMATION (COUCHE SILVER)")
    logger.info("==================================================")
    start_total = time.time()
    results: List[TransformationResult] = []

    # 1. RTE éCO2mix
    logger.info(">>> Étape 1/3 : Transformation RTE éCO2mix National...")
    try:
        rte_res = transform_rte_national_bronze_to_silver()
        results.append(rte_res)
    except Exception as e:
        logger.error(f"Échec transformation RTE : {e}", exc_info=True)
        raise

    # 2. Enedis Registre National
    logger.info(">>> Étape 2/3 : Transformation Registre National Enedis...")
    try:
        enedis_res = transform_enedis_registre_bronze_to_silver()
        results.append(enedis_res)
    except Exception as e:
        logger.error(f"Échec transformation Enedis : {e}", exc_info=True)
        raise

    # 3. Banque Mondiale
    logger.info(">>> Étape 3/3 : Transformation Banque Mondiale...")
    try:
        wb_res = transform_world_bank_bronze_to_silver()
        results.append(wb_res)
    except Exception as e:
        logger.error(f"Échec transformation Banque Mondiale : {e}", exc_info=True)
        raise

    total_duration = round(time.time() - start_total, 2)
    logger.info("==================================================")
    logger.info(f"FIN DU PIPELINE SILVER — Durée totale : {total_duration} s")
    logger.info("==================================================")
    return results


if __name__ == "__main__":
    results = run_all_silver_transformations()
    print("\n" + "=" * 70)
    print("BILAN COMPLET DU PIPELINE DE TRANSFORMATION SILVER")
    print("=" * 70)
    for r in results:
        print(f"\n[Source] {r.source_name}")
        print(f"  - Statut           : {r.status}")
        print(f"  - Lignes entrantes : {r.total_input_rows:,}")
        print(f"  - Lignes valides   : {r.valid_output_rows:,}")
        print(f"  - Lignes rejetées  : {r.rejected_rows:,}")
        print(f"  - Fichier Parquet  : {r.silver_output_path}")
        if r.rejected_output_path:
            print(f"  - Fichier rejets   : {r.rejected_output_path}")
        print(f"  - Colonnes ({len(r.columns)}) : {', '.join(r.columns[:6])}...")
        print(f"  - Durée            : {r.duration_seconds} s")
    print("\n" + "=" * 70)
