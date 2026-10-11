"""Transformation et nettoyage des données Enedis Registre National (Bronze vers Silver).

Règles de transformation appliquées :
1. Normalisation des noms de colonnes en snake_case strict avec unités explicites (_kw, _kwh).
2. Préservation rigoureuse des codes géographiques (INSEE, Département, IRIS, EPCI) au format string
   pour éviter la troncation des zéros initiaux (ex: '01', '2A').
3. Conversion des dates au format ISO standard (gestion des formats français DD/MM/YYYY).
4. Typage strict des puissances (puis_max_installee_kw en float) et comptages (nb_installations).
5. Contrôle qualité et détection des anomalies :
   - puis_max_installee_kw >= 0
   - filiere renseignée et valide
6. Rejets : les anomalies éventuelles sont tracées dans data/rejected/.
7. Sauvegarde en Couche Silver au format Parquet optimisé (pyarrow).
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


def transform_enedis_registre_bronze_to_silver(
    bronze_file: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    rejected_dir: Optional[Path] = None,
) -> TransformationResult:
    """Transforme le fichier brut du Registre National Enedis vers la couche Silver.

    Args:
        bronze_file: Chemin vers le CSV brut (défaut : dernier fichier dans settings.ENEDIS_RAW_DIR).
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
        candidates = sorted(settings.ENEDIS_RAW_DIR.glob("enedis_registre_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"Aucun fichier brut Enedis trouvé dans {settings.ENEDIS_RAW_DIR}. Lancez d'abord l'ingestion."
            )
        input_path = candidates[-1]
    else:
        input_path = bronze_file

    logger.info(f"[Enedis Silver] Début de la transformation depuis : {input_path}")

    # 2. Détection du séparateur
    with open(input_path, mode="r", encoding="utf-8-sig") as f:
        first_line = f.readline()
    sep = ";" if ";" in first_line else ","

    # 3. Lecture avec types strings par défaut pour les codes administratifs
    # afin d'éviter la conversion de '01' en 1 ou '2A' en NaN
    string_cols = [
        "codeEICResourceObject",
        "codeIRIS",
        "codeINSEECommune",
        "commune",
        "codeEPCI",
        "EPCI",
        "codeDepartement",
        "departement",
        "codeRegion",
        "region",
        "codeIRISCommuneImplantation",
        "codeINSEECommuneImplantation",
        "codeS3RENR",
        "codeFiliere",
        "filiere",
        "codeCombustible",
        "combustible",
        "codeTechnologie",
        "technologie",
        "typeStockage",
        "posteSource",
        "tensionRaccordement",
        "modeRaccordement",
        "regime",
        "codeGestionnaire",
        "gestionnaire",
    ]
    dtype_dict = {col: str for col in string_cols}

    df = pd.read_csv(
        input_path,
        sep=sep,
        encoding="utf-8-sig",
        dtype=dtype_dict,
        low_memory=False,
    )
    total_input_rows = len(df)
    logger.info(f"[Enedis Silver] Lignes lues : {total_input_rows:,}")

    # 4. Normalisation des noms de colonnes
    rename_mapping = {col: clean_column_name(col) for col in df.columns}
    df.rename(columns=rename_mapping, inplace=True)

    # 5. Conversion des puissances et grandeurs énergétiques en numériques
    numeric_cols = [
        "puis_max_installee_kw",
        "puis_max_rac_charge_kw",
        "puis_max_charge_kw",
        "puis_max_rac_kw",
        "puis_max_installee_discharge_kw",
        "max_puis_kw",
        "nb_groupes",
        "nb_installations",
        "energie_stockable_kwh",
        "capacite_reservoir",
        "hauteur_chute_m",
        "productible",
        "debit_maximal_m3_s",
        "energie_annuelle_glissante_injectee_kwh",
        "energie_annuelle_glissante_produite_kwh",
        "energie_annuelle_glissante_soutiree_kwh",
        "energie_annuelle_glissante_stockee_kwh",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6. Conversion des dates en format datetime / ISO
    date_cols = [
        "date_raccordement",
        "date_deraccordement",
        "date_mise_en_service",
        "date_debut_version",
        "date_mise_en_service_iso",
    ]
    for col in date_cols:
        if col in df.columns:
            if col == "date_mise_en_service_iso":
                df[col] = pd.to_datetime(df[col], errors="coerce", format="%Y-%m-%d")
            else:
                df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed", dayfirst=True)

    # 6. Élimination des colonnes 100% vides, quasi-vides (>85% nulls sans valeur analytique) ou redondantes
    empty_and_redundant_cols = [
        "energie_annuelle_glissante_stockee_kwh",   # 100% NULL
        "date_deraccordement",                      # 99.98% NULL
        "codes_combustibles_secondaires",           # 99.96% NULL
        "combustibles_secondaires",                 # 99.96% NULL
        "type_stockage",                            # 99.40% NULL
        "energie_annuelle_glissante_produite_kwh",  # 99.25% NULL
        "combustible",                              # 98.79% NULL
        "code_combustible",                         # 96.85% NULL
        "code_iris_commune_implantation",           # 92.21% NULL
        "puis_max_installee_discharge_kw",          # 91.40% NULL
        "energie_annuelle_glissante_soutiree_kwh",  # 91.32% NULL
        "puis_max_rac_charge_kw",                   # 91.08% NULL
        "puis_max_charge_kw",                       # 91.05% NULL
        "nb_groupes",                               # 85.10% NULL
        "code_s3renr",                              # 74.05% NULL
        "code_insee_commune_implantation",          # Redondant avec code_insee_commune
        "max_puis_kw",                              # Doublon strict de puis_max_installee_kw
        "date_mise_en_service_iso",                 # Doublon de date_mise_en_service
    ]
    dropped = [c for c in empty_and_redundant_cols if c in df.columns]
    df.drop(columns=dropped, inplace=True)
    logger.info(f"[Enedis Silver] {len(dropped)} colonnes vides/redondantes éliminées : {dropped}")

    # 7. Contrôles qualité stricts et détection des anomalies
    df["rejection_reason"] = pd.NA

    # Règle Q1 : Capacité installée positive et non nulle (élimine les lignes sans information de puissance)
    if "puis_max_installee_kw" in df.columns:
        invalid_capacity = df["puis_max_installee_kw"].isna() | (df["puis_max_installee_kw"] <= 0)
        df.loc[invalid_capacity & df["rejection_reason"].isna(), "rejection_reason"] = "Capacité installée manquante ou <= 0 kW"

    # Règle Q2 : Filière non vide et valide
    if "filiere" in df.columns:
        invalid_filiere = df["filiere"].isna() | (df["filiere"].str.strip() == "")
        df.loc[invalid_filiere & df["rejection_reason"].isna(), "rejection_reason"] = "Filière de production manquante"

    # Règle Q3 : Localisation géographique minimale (élimine les lignes fantômes sans commune, ni dpt, ni région)
    geo_cols = [c for c in ["commune", "code_departement", "region"] if c in df.columns]
    if geo_cols:
        no_geo = df[geo_cols].isna().all(axis=1)
        df.loc[no_geo & df["rejection_reason"].isna(), "rejection_reason"] = "Localisation géographique totalement absente"

    rejected_rows_count = 0
    rejected_path_str: Optional[str] = None
    is_rejected = df["rejection_reason"].notna()

    if is_rejected.any():
        df_rej = df[is_rejected].copy()
        rejected_rows_count = len(df_rej)

        date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
        rej_file = rej_dir / f"enedis_rejected_{date_tag}.csv"
        df_rej.to_csv(rej_file, index=False, sep=";", encoding="utf-8")
        rejected_path_str = str(rej_file)
        logger.warning(
            f"[Enedis Silver] {rejected_rows_count} lignes rejetées consignées dans {rej_file}"
        )
        df_valid = df[~is_rejected].copy().drop(columns=["rejection_reason"])
    else:
        df_valid = df.copy().drop(columns=["rejection_reason"])

    # Dédoublonnage exact si des lignes sont 100% identiques
    df_valid.drop_duplicates(inplace=True)
    df_valid.reset_index(drop=True, inplace=True)

    # 8. Sauvegarde en Couche Silver (Parquet + CSV échantillon)
    silver_output_path = dest_dir / "silver_enedis_registre_2025.parquet"
    df_valid.to_parquet(silver_output_path, engine="pyarrow", index=False)

    sample_preview_path = dest_dir / "silver_enedis_registre_2025_sample.csv"
    df_valid.head(100).to_csv(sample_preview_path, index=False, sep=";", encoding="utf-8")

    duration = round(time.time() - start_time, 2)
    valid_rows = len(df_valid)
    logger.info(
        f"[Enedis Silver] Transformation terminée : {valid_rows:,} installations nettoyées "
        f"enregistrées dans {silver_output_path} ({duration} s)."
    )

    return TransformationResult(
        status="SUCCESS",
        source_name="ENEDIS_REGISTRE_INSTALLATIONS",
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
    result = transform_enedis_registre_bronze_to_silver()
    print("\n--- Résultat Transformation Enedis Silver ---")
    print(f"Statut             : {result.status}")
    print(f"Lignes d'entrée    : {result.total_input_rows:,}")
    print(f"Lignes valides     : {result.valid_output_rows:,}")
    print(f"Lignes rejetées    : {result.rejected_rows:,}")
    print(f"Fichier Parquet    : {result.silver_output_path}")
    print(f"Durée d'exécution  : {result.duration_seconds} s")

