"""Transformation et nettoyage des données Banque Mondiale (Bronze vers Silver).

Règles de transformation appliquées :
1. Aplatissement de la structure hiérarchique JSON (indicateur, pays, observations).
2. Préservation de l'intégralité de la série temporelle (1960-2025) :
   - Traçabilité explicite des valeurs manquantes via l'indicateur booléen `is_missing`.
3. Typage strict :
   - year en integer
   - valeur en float (pourcentage entre 0 et 100)
4. Contrôle qualité et validation :
   - Année cohérente (1900 <= year <= 2100)
   - Code pays ISO3 conforme ('FRA')
   - Valeur comprise entre 0% et 100%
5. Rejets : traçabilité des anomalies dans data/rejected/.
6. Sauvegarde en Couche Silver au format Parquet optimisé (pyarrow).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Optional

import pandas as pd

from config.settings import settings
from src.energy_observatory.transformation.cleaning import TransformationResult
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


def transform_world_bank_bronze_to_silver(
    bronze_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    rejected_dir: Optional[Path] = None,
) -> TransformationResult:
    """Transforme le fichier JSON brut de la Banque Mondiale vers la couche Silver.

    Args:
        bronze_file: Chemin vers le JSON brut (défaut : dernier fichier dans settings.WORLDBANK_RAW_DIR).
        output_dir: Dossier de destination Silver (défaut : settings.DATA_PROCESSED_DIR).
        rejected_dir: Dossier des rejets (défaut : settings.DATA_REJECTED_DIR).

    Returns:
        TransformationResult: Rapport détaillé de la transformation.
    """
    start_time = time.time()
    dest_dir = output_dir or settings.DATA_PROCESSED_DIR
    rej_dir = rejected_dir or settings.DATA_REJECTED_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    rej_dir.mkdir(parents=True, exist_ok=True)

    # 1. Sélection du fichier Bronze d'entrée
    if bronze_file is None:
        candidates = sorted(settings.WORLDBANK_RAW_DIR.glob("worldbank_*.json"))
        # Exclure les fichiers de métadonnées
        candidates = [c for c in candidates if not c.name.endswith("_metadata.json")]
        if not candidates:
            raise FileNotFoundError(
                f"Aucun fichier brut Banque Mondiale trouvé dans {settings.WORLDBANK_RAW_DIR}. Lancez d'abord l'ingestion."
            )
        input_path = candidates[-1]
    else:
        input_path = bronze_file

    logger.info(f"[World Bank Silver] Début de la transformation depuis : {input_path}")

    # 2. Lecture du fichier JSON
    with open(input_path, mode="r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list) or len(raw_data) < 2 or not isinstance(raw_data[1], list):
        raise ValueError(
            f"Structure JSON World Bank inattendue dans {input_path} (attendu: [metadata, observations])."
        )

    observations = raw_data[1]
    total_input_rows = len(observations)
    logger.info(f"[World Bank Silver] Observations lues : {total_input_rows}")

    # 3. Aplatissement structuré
    records = []
    for obs in observations:
        indicator_id = obs.get("indicator", {}).get("id")
        indicator_name = obs.get("indicator", {}).get("value")
        country_iso2 = obs.get("country", {}).get("id")
        country_name = obs.get("country", {}).get("value")
        country_iso3 = obs.get("countryiso3code")
        raw_year = obs.get("date")
        raw_val = obs.get("value")

        # Parsing de l'année
        try:
            year = int(raw_year) if raw_year is not None else None
        except (ValueError, TypeError):
            year = None

        # Parsing de la valeur
        is_missing = raw_val is None
        try:
            val = float(raw_val) if not is_missing else None
        except (ValueError, TypeError):
            val = None

        records.append({
            "indicator_id": indicator_id,
            "indicator_name": indicator_name,
            "country_iso2": country_iso2,
            "country_name": country_name,
            "country_iso3": country_iso3,
            "year": year,
            "valeur_pct": val,
            "is_missing": is_missing,
            "unit": "% of population",
        })

    df = pd.DataFrame(records)

    # 4. Contrôles qualité et détection des anomalies
    rejected_masks = []
    rejection_reasons = []

    # Règle Q1 : Année valide
    invalid_year = df["year"].isna() | (df["year"] < 1900) | (df["year"] > 2100)
    if invalid_year.any():
        rejected_masks.append(invalid_year)
        rejection_reasons.append("Année invalide (< 1900 ou > 2100)")

    # Règle Q2 : Code ISO3 valide
    invalid_country = df["country_iso3"].isna() | (df["country_iso3"] != "FRA")
    if invalid_country.any():
        rejected_masks.append(invalid_country)
        rejection_reasons.append("Code pays ISO3 invalide ou différent de FRA")

    # Règle Q3 : Valeur entre 0% et 100% (pour les valeurs renseignées)
    invalid_val = (
        df["valeur_pct"].notna()
        & ((df["valeur_pct"] < 0.0) | (df["valeur_pct"] > 100.0))
    )
    if invalid_val.any():
        rejected_masks.append(invalid_val)
        rejection_reasons.append("Valeur hors bornes [0%, 100%]")

    # Règle Q4 : Dédoublonnage sur indicator_id et year
    dup_mask = df.duplicated(subset=["indicator_id", "year"], keep="first")
    if dup_mask.any():
        rejected_masks.append(dup_mask)
        rejection_reasons.append("Doublon sur indicator_id + year")

    rejected_rows_count = 0
    rejected_path_str: Optional[str] = None

    if rejected_masks:
        combined_rejected = pd.concat([m for m in rejected_masks], axis=1).any(axis=1)
        if combined_rejected.any():
            df_rej = df[combined_rejected].copy()
            df_rej["rejection_reason"] = "Anomalie Banque Mondiale"
            rejected_rows_count = len(df_rej)

            date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
            rej_file = rej_dir / f"worldbank_rejected_{date_tag}.csv"
            df_rej.to_csv(rej_file, index=False, sep=";", encoding="utf-8")
            rejected_path_str = str(rej_file)
            logger.warning(
                f"[World Bank Silver] {rejected_rows_count} lignes rejetées consignées dans {rej_file}"
            )
            df_valid = df[~combined_rejected].copy()
        else:
            df_valid = df.copy()
    else:
        df_valid = df.copy()

    # Tri chronologique ascendant (1960 -> 2025)
    df_valid.sort_values(by="year", ascending=True, inplace=True)
    df_valid.reset_index(drop=True, inplace=True)

    # 5. Sauvegarde en Couche Silver (Parquet + CSV échantillon)
    silver_output_path = dest_dir / "silver_worldbank_access_electricity.parquet"
    df_valid.to_parquet(silver_output_path, engine="pyarrow", index=False)

    sample_preview_path = dest_dir / "silver_worldbank_access_electricity_sample.csv"
    df_valid.to_csv(sample_preview_path, index=False, sep=";", encoding="utf-8")

    duration = round(time.time() - start_time, 2)
    valid_rows = len(df_valid)
    logger.info(
        f"[World Bank Silver] Transformation terminée : {valid_rows} observations "
        f"enregistrées dans {silver_output_path} ({duration} s)."
    )

    return TransformationResult(
        status="SUCCESS",
        source_name="WORLDBANK_ACCESS_ELECTRICITY",
        bronze_input_path=str(input_path),
        silver_output_path=str(silver_output_path),
        rejected_output_path=rejected_path_str,
        total_input_rows=total_input_rows,
        valid_output_rows=valid_rows,
        rejected_rows=rejected_rows_count,
        columns=list(df_valid.columns),
        duration_seconds=duration,
    )


if __name__ == "__main__":
    result = transform_world_bank_bronze_to_silver()
    print("\n--- Résultat Transformation Banque Mondiale Silver ---")
    print(f"Statut             : {result.status}")
    print(f"Lignes d'entrée    : {result.total_input_rows:,}")
    print(f"Lignes valides     : {result.valid_output_rows:,}")
    print(f"Lignes rejetées    : {result.rejected_rows:,}")
    print(f"Fichier Parquet    : {result.silver_output_path}")
    print(f"Durée d'exécution  : {result.duration_seconds} s")

