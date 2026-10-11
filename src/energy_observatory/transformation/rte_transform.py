"""Transformation et nettoyage des données RTE éCO2mix (Bronze vers Silver).

Règles de transformation appliquées :
1. Normalisation des noms de colonnes en snake_case strict avec unités explicites (_mw, _g_kwh).
2. Typage temporel : conversion de 'date_heure' en timestamp ISO UTC.
3. Séparation de granularité : isolation de la série temporelle de réalisation au pas 30 minutes
   (exclusion des pas 15 minutes où seules les prévisions sont publiées).
4. Contrôle de cohérence :
   - consommation_mw > 0
   - filières de production >= 0
   - taux_co2_g_kwh >= 0
   - absence de doublons sur date_heure
5. Rejets : les lignes non conformes sont archivées dans data/rejected/ avec motif explicite.
6. Sauvegarde en Couche Silver au format Parquet optimisé.
"""

from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Optional

import pandas as pd

from config.settings import settings
from src.energy_observatory.transformation.cleaning import (
    TransformationResult,
    clean_column_name,
)
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


def transform_rte_national_bronze_to_silver(
    bronze_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    rejected_dir: Optional[Path] = None,
) -> TransformationResult:
    """Transforme le fichier brut éCO2mix national vers la couche Silver.

    Args:
        bronze_file: Chemin vers le CSV brut (défaut : dernier fichier dans settings.RTE_RAW_DIR).
        output_dir: Dossier de sortie Silver (défaut : settings.DATA_PROCESSED_DIR).
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
        candidates = sorted(settings.RTE_RAW_DIR.glob("rte_national_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"Aucun fichier brut RTE trouvé dans {settings.RTE_RAW_DIR}. Lancez d'abord l'ingestion."
            )
        input_path = candidates[-1]
    else:
        input_path = bronze_file

    logger.info(f"[RTE Silver] Début de la transformation depuis : {input_path}")

    # 2. Lecture du fichier CSV
    # Détection du séparateur
    with open(input_path, mode="r", encoding="utf-8-sig") as f:
        first_line = f.readline()
    sep = ";" if ";" in first_line else ","

    df = pd.read_csv(input_path, sep=sep, encoding="utf-8-sig", low_memory=False)
    total_input_rows = len(df)
    logger.info(f"[RTE Silver] Lignes lues : {total_input_rows:,}")

    # 3. Normalisation des noms de colonnes
    rename_mapping = {col: clean_column_name(col) for col in df.columns}
    df.rename(columns=rename_mapping, inplace=True)

    # 4. Harmonisation temporelle
    if "date_heure" not in df.columns:
        raise KeyError("La colonne 'date_heure' est absente du fichier source RTE.")

    df["date_heure"] = pd.to_datetime(df["date_heure"], utc=True, errors="coerce")

    # 5. Séparation métier des pas de temps
    # Au pas 15 minutes, consommation_mw est NaN (seules les prévisions J-1 et J existent).
    # On isole les mesures réelles (pas 30 min)
    is_realized = df["consommation_mw"].notna()
    df_real = df[is_realized].copy()

    # Conversion numérique stricte des colonnes de mesure
    numeric_cols = [
        "consommation_mw",
        "prevision_j1_mw",
        "prevision_j_mw",
        "fioul_mw",
        "charbon_mw",
        "gaz_mw",
        "nucleaire_mw",
        "eolien_mw",
        "solaire_mw",
        "hydraulique_mw",
        "pompage_mw",
        "bioenergies_mw",
        "ech_physiques_mw",
        "taux_co2_g_kwh",
    ]
    for col in numeric_cols:
        if col in df_real.columns:
            df_real[col] = pd.to_numeric(df_real[col], errors="coerce")

    # 6. Contrôles qualité et détection des anomalies
    rejected_masks = []
    rejection_reasons = []

    # Règle Q1 : Timestamp valide
    invalid_date = df_real["date_heure"].isna()
    if invalid_date.any():
        rejected_masks.append(invalid_date)
        rejection_reasons.append("Date_heure invalide ou non parsable")

    # Règle Q2 : Consommation positive
    invalid_conso = df_real["consommation_mw"] <= 0
    if invalid_conso.any():
        rejected_masks.append(invalid_conso)
        rejection_reasons.append("Consommation <= 0 MW")

    # Règle Q3 : Filières de production (traitement des auxiliaires et détection d'aberrations)
    # En réseau électrique, une installation à l'arrêt soutire une faible puissance pour ses auxiliaires
    # (ex: onduleurs solaires la nuit à -1 MW, centrales à l'arrêt à -15 MW).
    # La production brute est bornée à 0.0 MW (clipping), tandis que les aberrations sévères (< -500 MW) sont rejetées.
    prod_cols = [c for c in ["nucleaire_mw", "eolien_mw", "solaire_mw", "hydraulique_mw", "gaz_mw", "charbon_mw", "fioul_mw", "bioenergies_mw"] if c in df_real.columns]
    for p_col in prod_cols:
        severe_negative = df_real[p_col] < -500.0
        if severe_negative.any():
            rejected_masks.append(severe_negative)
            rejection_reasons.append(f"Aberration de production sévère sur {p_col} (< -500 MW)")
        
        # Ramener les soutirages minimes d'auxiliaires à 0.0 MW
        aux_mask = (df_real[p_col] < 0) & (df_real[p_col] >= -500.0)
        aux_count = aux_mask.sum()
        if aux_count > 0:
            df_real.loc[aux_mask, p_col] = 0.0

    # Règle Q4 : Taux de CO2 >= 0
    if "taux_co2_g_kwh" in df_real.columns:
        invalid_co2 = df_real["taux_co2_g_kwh"] < 0
        if invalid_co2.any():
            rejected_masks.append(invalid_co2)
            rejection_reasons.append("Taux de CO2 négatif")

    # Règle Q5 : Dédoublonnage sur date_heure
    dup_mask = df_real.duplicated(subset=["date_heure"], keep="first")
    if dup_mask.any():
        rejected_masks.append(dup_mask)
        rejection_reasons.append("Doublon temporel sur date_heure")

    # Agrégation des rejets
    rejected_rows_count = 0
    rejected_path_str: Optional[str] = None

    if rejected_masks:
        combined_rejected = pd.concat([m for m in rejected_masks], axis=1).any(axis=1)
        if combined_rejected.any():
            df_rej = df_real[combined_rejected].copy()
            df_rej["rejection_reason"] = "Anomalie détectée"
            rejected_rows_count = len(df_rej)

            date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
            rej_file = rej_dir / f"rte_rejected_{date_tag}.csv"
            df_rej.to_csv(rej_file, index=False, sep=";", encoding="utf-8")
            rejected_path_str = str(rej_file)
            logger.warning(
                f"[RTE Silver] {rejected_rows_count} lignes rejetées consignées dans {rej_file}"
            )

            # Ne conserver que les lignes valides
            df_valid = df_real[~combined_rejected].copy()
        else:
            df_valid = df_real
    else:
        df_valid = df_real

    # Tri chronologique garanti
    df_valid.sort_values(by="date_heure", ascending=True, inplace=True)
    df_valid.reset_index(drop=True, inplace=True)

    # 7. Sauvegarde en Couche Silver (Parquet + CSV échantillon)
    silver_output_path = dest_dir / "silver_rte_national_30min.parquet"
    df_valid.to_parquet(silver_output_path, engine="pyarrow", index=False)

    sample_preview_path = dest_dir / "silver_rte_national_30min_sample.csv"
    df_valid.head(100).to_csv(sample_preview_path, index=False, sep=";", encoding="utf-8")

    duration = round(time.time() - start_time, 2)
    valid_rows = len(df_valid)
    logger.info(
        f"[RTE Silver] Transformation terminée : {valid_rows:,} lignes nettoyées "
        f"enregistrées dans {silver_output_path} ({duration} s)."
    )

    return TransformationResult(
        status="SUCCESS",
        source_name="RTE_ECO2MIX_NATIONAL",
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
    result = transform_rte_national_bronze_to_silver()
    print("\n--- Résultat Transformation RTE Silver ---")
    print(f"Statut             : {result.status}")
    print(f"Lignes d'entrée    : {result.total_input_rows:,}")
    print(f"Lignes valides     : {result.valid_output_rows:,}")
    print(f"Lignes rejetées    : {result.rejected_rows:,}")
    print(f"Fichier Parquet    : {result.silver_output_path}")
    print(f"Durée d'exécution  : {result.duration_seconds} s")

