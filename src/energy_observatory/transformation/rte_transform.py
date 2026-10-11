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

    # Conversion numérique stricte de toutes les colonnes de mesure et échanges
    exclude_cols = {"perimetre", "nature", "date", "heure", "date_heure"}
    for col in df_real.columns:
        if col not in exclude_cols:
            df_real[col] = pd.to_numeric(
                df_real[col].astype(str).str.strip().replace(["ND", "-", "", "nan"], pd.NA),
                errors="coerce",
            )

    # 6. Contrôles qualité et détection des anomalies
    df_real["rejection_reason"] = pd.NA

    # Règle Q1 : Timestamp valide
    invalid_date = df_real["date_heure"].isna()
    if invalid_date.any():
        df_real.loc[invalid_date, "rejection_reason"] = "Date_heure invalide ou non parsable"

    # Règle Q2 : Consommation positive
    invalid_conso = df_real["consommation_mw"] <= 0
    if invalid_conso.any():
        df_real.loc[invalid_conso & df_real["rejection_reason"].isna(), "rejection_reason"] = "Consommation <= 0 MW ou manquante"

    # Règle Q3 : Filières de production (traitement des auxiliaires et détection d'aberrations)
    prod_cols = [c for c in ["nucleaire_mw", "eolien_mw", "solaire_mw", "hydraulique_mw", "gaz_mw", "charbon_mw", "fioul_mw", "bioenergies_mw"] if c in df_real.columns]
    for p_col in prod_cols:
        severe_negative = df_real[p_col] < -500.0
        if severe_negative.any():
            df_real.loc[severe_negative & df_real["rejection_reason"].isna(), "rejection_reason"] = f"Aberration de production sévère sur {p_col} (< -500 MW)"

        # Ramener les soutirages minimes d'auxiliaires à 0.0 MW
        aux_mask = (df_real[p_col] < 0) & (df_real[p_col] >= -500.0)
        aux_count = aux_mask.sum()
        if aux_count > 0:
            df_real.loc[aux_mask, p_col] = 0.0

    # Règle Q4 : Taux de CO2 >= 0
    if "taux_co2_g_kwh" in df_real.columns:
        invalid_co2 = df_real["taux_co2_g_kwh"] < 0
        if invalid_co2.any():
            df_real.loc[invalid_co2 & df_real["rejection_reason"].isna(), "rejection_reason"] = "Taux de CO2 négatif"

    # Règle Q5 : Dédoublonnage sur date_heure (ex: passage à l'heure d'hiver)
    dup_mask = df_real.duplicated(subset=["date_heure"], keep="first")
    if dup_mask.any():
        df_real.loc[dup_mask & df_real["rejection_reason"].isna(), "rejection_reason"] = "Doublon temporel UTC (transition heure d'été/hiver)"

    # Agrégation des rejets
    rejected_rows_count = 0
    rejected_path_str: Optional[str] = None
    is_rejected = df_real["rejection_reason"].notna()

    if is_rejected.any():
        df_rej = df_real[is_rejected].copy()
        rejected_rows_count = len(df_rej)

        date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
        rej_file = rej_dir / f"rte_rejected_{date_tag}.csv"
        df_rej.to_csv(rej_file, index=False, sep=";", encoding="utf-8")
        rejected_path_str = str(rej_file)
        logger.warning(
            f"[RTE Silver] {rejected_rows_count} lignes rejetées consignées dans {rej_file}"
        )
        df_valid = df_real[~is_rejected].copy().drop(columns=["rejection_reason"])
    else:
        df_valid = df_real.copy().drop(columns=["rejection_reason"])

    # Tri chronologique garanti
    df_valid.sort_values(by="date_heure", ascending=True, inplace=True)
    df_valid.reset_index(drop=True, inplace=True)

    # 7. Élimination des 13 sous-filières vides en 2012 pour garantir un jeu de données 100% complet
    sub_tech_cols = [
        "fioul_tac_mw",
        "fioul_cogeneration_mw",
        "fioul_autres_mw",
        "gaz_tac_mw",
        "gaz_cogeneration_mw",
        "gaz_ccg_mw",
        "gaz_autres_mw",
        "hydraulique_fil_de_l_eau_eclusee_mw",
        "hydraulique_lacs_mw",
        "hydraulique_step_turbinage_mw",
        "bioenergies_dechets_mw",
        "bioenergies_biomasse_mw",
        "bioenergies_biogaz_mw",
    ]
    dropped_sub = [c for c in sub_tech_cols if c in df_valid.columns]
    df_valid.drop(columns=dropped_sub, inplace=True)
    logger.info(f"[RTE Silver] {len(dropped_sub)} sous-filières éliminées pour homogénéité 2012-2026")

    # 8. Sauvegarde en Couche Silver (Parquet + CSV échantillon)
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

