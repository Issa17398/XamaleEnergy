"""Pipeline de chargement de la Couche Silver vers la Couche Gold (PostgreSQL).

Ce module ingère les fichiers Parquet nettoyés et alimente le modèle en étoile :
- gold.dim_temps
- gold.dim_geographie
- gold.dim_filiere
- gold.fact_electricite_national_30min
- gold.fact_registre_installations
- gold.fact_acces_electricite_annuel
"""

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import time
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.settings import settings
from src.energy_observatory.storage.db import get_engine, init_database
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class GoldLoadReport:
    """Rapport d'exécution du chargement de la Couche Gold."""

    status: str
    rows_dim_temps: int = 0
    rows_dim_geographie: int = 0
    rows_fact_electricite: int = 0
    rows_fact_registre: int = 0
    rows_fact_worldbank: int = 0
    duration_seconds: float = 0.0
    errors: Optional[List[str]] = None


def _fast_copy_df(
    df: pd.DataFrame,
    table_name: str,
    schema: str,
    engine: Engine,
    columns: Optional[List[str]] = None,
) -> int:
    """Charge un DataFrame à très haute vitesse via le protocole PostgreSQL COPY.

    Args:
        df: DataFrame à insérer.
        table_name: Nom de la table cible.
        schema: Schéma PostgreSQL ('gold' ou 'silver').
        engine: Moteur SQLAlchemy connecté.
        columns: Liste ordonnée des colonnes cibles (défaut : colonnes du DataFrame).

    Returns:
        int: Nombre de lignes insérées.
    """
    if df.empty:
        return 0

    cols = columns or list(df.columns)
    df_subset = df[cols].copy()

    # Préparation du flux CSV en mémoire
    buffer = StringIO()
    df_subset.to_csv(
        buffer,
        index=False,
        header=False,
        sep="\t",
        na_rep="\\N",
        encoding="utf-8",
    )
    buffer.seek(0)

    # Récupération de la connexion brute DBAPI (psycopg2)
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cols_str = ", ".join([f'"{c}"' for c in cols])
            copy_sql = (
                f'COPY "{schema}"."{table_name}" ({cols_str}) '
                f"FROM STDIN WITH (FORMAT text, NULL '\\N')"
            )
            cursor.copy_expert(sql=copy_sql, file=buffer)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()

    return len(df_subset)


def load_dim_temps(
    rte_parquet_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> int:
    """Génère et peuple la dimension temporelle 'gold.dim_temps'.

    Args:
        rte_parquet_path: Fichier Parquet RTE source.
        engine: Moteur SQLAlchemy.

    Returns:
        int: Nombre de lignes chargées.
    """
    eng = engine or get_engine()
    parquet_path = rte_parquet_path or (settings.DATA_PROCESSED_DIR / "silver_rte_national_30min.parquet")

    logger.info(f"[Gold Loader] Alimentation de gold.dim_temps depuis {parquet_path.name}...")
    df = pd.read_parquet(parquet_path, columns=["date_heure"])
    df["date_heure"] = pd.to_datetime(df["date_heure"], utc=True)
    df.drop_duplicates(subset=["date_heure"], inplace=True)
    df.sort_values(by="date_heure", inplace=True)

    dt = df["date_heure"].dt

    # Dictionnaire des noms de mois et jours en français
    mois_map = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
        7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    jour_map = {
        1: "Lundi", 2: "Mardi", 3: "Mercredi", 4: "Jeudi", 5: "Vendredi", 6: "Samedi", 7: "Dimanche"
    }

    dim_temps = pd.DataFrame({
        "date_heure": df["date_heure"],
        "date": dt.date,
        "heure": dt.strftime("%H:%M"),
        "annee": dt.year,
        "mois": dt.month,
        "mois_nom": dt.month.map(mois_map),
        "jour": dt.day,
        "jour_semaine": dt.dayofweek + 1,  # 1=Lundi, 7=Dimanche
        "jour_semaine_nom": (dt.dayofweek + 1).map(jour_map),
        "trimestre": dt.quarter,
        "semaine": dt.isocalendar().week,
        "saison": dt.month.map(lambda m: "Hiver" if m in (12, 1, 2) else ("Printemps" if m in (3, 4, 5) else ("Été" if m in (6, 7, 8) else "Automne"))),
        "est_weekend": dt.dayofweek >= 5,
        "est_jour_ferie": False,
    })

    # Jours fériés fixes en France
    for (m, d) in [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)]:
        mask = (dim_temps["mois"] == m) & (dim_temps["jour"] == d)
        dim_temps.loc[mask, "est_jour_ferie"] = True

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.dim_temps CASCADE;"))

    count = _fast_copy_df(dim_temps, "dim_temps", "gold", eng)
    logger.info(f"[Gold Loader] {count:,} intervalles chargés dans gold.dim_temps.")
    return count


def load_dim_geographie(
    enedis_parquet_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> int:
    """Génère et peuple la dimension géographique 'gold.dim_geographie'.

    Args:
        enedis_parquet_path: Fichier Parquet Enedis source.
        engine: Moteur SQLAlchemy.

    Returns:
        int: Nombre de communes chargées.
    """
    eng = engine or get_engine()
    parquet_path = enedis_parquet_path or (settings.DATA_PROCESSED_DIR / "silver_enedis_registre_2025.parquet")

    logger.info(f"[Gold Loader] Alimentation de gold.dim_geographie depuis {parquet_path.name}...")
    geo_cols = [
        "code_insee_commune",
        "commune",
        "code_departement",
        "departement",
        "code_region",
        "region",
        "code_epci",
        "epci",
    ]
    df = pd.read_parquet(parquet_path, columns=geo_cols)
    df.dropna(subset=["code_insee_commune"], inplace=True)
    df = df[df["code_insee_commune"].astype(str).str.strip() != ""]
    df.drop_duplicates(subset=["code_insee_commune"], inplace=True)
    df.sort_values(by="code_insee_commune", inplace=True)

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.dim_geographie CASCADE;"))

    count = _fast_copy_df(df, "dim_geographie", "gold", eng, columns=geo_cols)
    logger.info(f"[Gold Loader] {count:,} communes chargées dans gold.dim_geographie.")
    return count


def load_fact_electricite_national_30min(
    rte_parquet_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> int:
    """Charge la table de faits électricité nationale 30 minutes.

    Args:
        rte_parquet_path: Fichier Parquet RTE source.
        engine: Moteur SQLAlchemy.

    Returns:
        int: Nombre de lignes chargées.
    """
    eng = engine or get_engine()
    parquet_path = rte_parquet_path or (settings.DATA_PROCESSED_DIR / "silver_rte_national_30min.parquet")

    logger.info(f"[Gold Loader] Alimentation de fact_electricite_national_30min depuis {parquet_path.name}...")
    df = pd.read_parquet(parquet_path)

    fact_cols = [
        "date_heure",
        "consommation_mw",
        "prevision_j1_mw",
        "prevision_j_mw",
        "nucleaire_mw",
        "eolien_mw",
        "solaire_mw",
        "hydraulique_mw",
        "pompage_mw",
        "gaz_mw",
        "charbon_mw",
        "fioul_mw",
        "bioenergies_mw",
        "ech_physiques_mw",
        "taux_co2_g_kwh",
        "ech_comm_angleterre_mw",
        "ech_comm_espagne_mw",
        "ech_comm_italie_mw",
        "ech_comm_suisse_mw",
        "ech_comm_allemagne_belgique_mw",
    ]

    # Filtrer les colonnes existantes
    valid_cols = [c for c in fact_cols if c in df.columns]
    df_subset = df[valid_cols].copy()
    df_subset["date_heure"] = pd.to_datetime(df_subset["date_heure"], utc=True)

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.fact_electricite_national_30min CASCADE;"))

    count = _fast_copy_df(df_subset, "fact_electricite_national_30min", "gold", eng, columns=valid_cols)
    logger.info(f"[Gold Loader] {count:,} lignes chargées dans fact_electricite_national_30min.")
    return count


def _map_filiere_code(filiere_raw: Optional[str]) -> str:
    """Mappe la filière brute Enedis vers le code normalisé de dim_filiere."""
    if not filiere_raw or pd.isna(filiere_raw):
        return "autre"
    val = str(filiere_raw).strip().lower()
    if "solaire" in val or "photovolta" in val:
        return "solaire"
    if "eolien" in val or "éolien" in val:
        return "eolien"
    if "hydraulique" in val or "hydro" in val:
        return "hydraulique"
    if "bio" in val or "biomasse" in val or "biogaz" in val or "dechet" in val:
        return "bioenergies"
    if "nucleaire" in val or "nucléaire" in val:
        return "nucleaire"
    if "gaz" in val:
        return "gaz"
    if "charbon" in val:
        return "charbon"
    if "fioul" in val:
        return "fioul"
    if "stockage" in val or "batterie" in val:
        return "stockage"
    return "autre"


def load_fact_registre_installations(
    enedis_parquet_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> int:
    """Charge la table de faits des installations de production Enedis.

    Args:
        enedis_parquet_path: Fichier Parquet Enedis source.
        engine: Moteur SQLAlchemy.

    Returns:
        int: Nombre d'installations chargées.
    """
    eng = engine or get_engine()
    parquet_path = enedis_parquet_path or (settings.DATA_PROCESSED_DIR / "silver_enedis_registre_2025.parquet")

    logger.info(f"[Gold Loader] Alimentation de fact_registre_installations depuis {parquet_path.name}...")
    df = pd.read_parquet(parquet_path)

    # Préparation du mapping
    df["code_filiere"] = df["filiere"].apply(_map_filiere_code) if "filiere" in df.columns else "autre"

    # Vérification des clés étrangères géographiques existantes dans dim_geographie
    with eng.connect() as conn:
        known_communes = set(
            row[0] for row in conn.execute(text("SELECT code_insee_commune FROM gold.dim_geographie;")).fetchall()
        )

    # Assurer l'intégrité référentielle
    df["code_insee_commune_fk"] = df["code_insee_commune"].apply(
        lambda c: c if c in known_communes else None
    )

    dest_cols = [
        "nom_installation",
        "code_eic",
        "code_insee_commune",
        "code_filiere",
        "filiere",
        "technologie",
        "combustible",
        "puis_max_installee_kw",
        "puis_max_raccordee_kw",
        "tension_raccordement",
        "date_mise_en_service",
        "annee_mise_en_service",
        "regime",
        "gestionnaire_reseau",
        "latitude",
        "longitude",
    ]

    target_df = pd.DataFrame()
    for col in dest_cols:
        if col == "code_insee_commune":
            target_df[col] = df["code_insee_commune_fk"]
        elif col in df.columns:
            target_df[col] = df[col]
        else:
            target_df[col] = None

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.fact_registre_installations CASCADE;"))

    count = _fast_copy_df(target_df, "fact_registre_installations", "gold", eng, columns=dest_cols)
    logger.info(f"[Gold Loader] {count:,} installations chargées dans fact_registre_installations.")
    return count


def load_fact_worldbank(
    worldbank_parquet_path: Optional[Path] = None,
    engine: Optional[Engine] = None,
) -> int:
    """Charge la table de faits Banque Mondiale.

    Args:
        worldbank_parquet_path: Fichier Parquet Banque Mondiale source.
        engine: Moteur SQLAlchemy.

    Returns:
        int: Nombre d'enregistrements chargés.
    """
    eng = engine or get_engine()
    parquet_path = worldbank_parquet_path or (settings.DATA_PROCESSED_DIR / "silver_worldbank_access_electricity.parquet")

    logger.info(f"[Gold Loader] Alimentation de fact_acces_electricite_annuel depuis {parquet_path.name}...")
    df = pd.read_parquet(parquet_path)

    target_df = pd.DataFrame({
        "annee": df["year"].astype(int),
        "pays_iso3": df["country_iso3"],
        "pays_nom": df["country_name"],
        "indicateur_id": df["indicator_id"],
        "valeur_pct": df["valeur_pct"],
        "is_missing": df["is_missing"].fillna(False).astype(bool),
    })

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.fact_acces_electricite_annuel CASCADE;"))

    count = _fast_copy_df(target_df, "fact_acces_electricite_annuel", "gold", eng)
    logger.info(f"[Gold Loader] {count:,} observations chargées dans fact_acces_electricite_annuel.")
    return count


def load_silver_to_gold(engine: Optional[Engine] = None) -> GoldLoadReport:
    """Exécute l'ensemble du pipeline de chargement vers la Couche Gold.

    1. Initialise les schémas et tables si nécessaire.
    2. Charge les dimensions (dim_temps, dim_geographie).
    3. Charge les tables de faits (fact_electricite, fact_registre, fact_worldbank).

    Returns:
        GoldLoadReport: Synthèse complète de l'ingestion Gold.
    """
    start_time = time.time()
    eng = engine or get_engine()

    try:
        # Étape 1 : Initialisation DDL
        init_database(eng)

        # Étape 2 : Chargement des dimensions
        n_temps = load_dim_temps(engine=eng)
        n_geo = load_dim_geographie(engine=eng)

        # Étape 3 : Chargement des faits
        n_elec = load_fact_electricite_national_30min(engine=eng)
        n_inst = load_fact_registre_installations(engine=eng)
        n_wb = load_fact_worldbank(engine=eng)

        duration = round(time.time() - start_time, 2)
        logger.info(
            f"[Gold Loader] Succès global en {duration} s : "
            f"Temps={n_temps:,}, Geo={n_geo:,}, Elec={n_elec:,}, Inst={n_inst:,}, WB={n_wb:,}"
        )

        return GoldLoadReport(
            status="SUCCESS",
            rows_dim_temps=n_temps,
            rows_dim_geographie=n_geo,
            rows_fact_electricite=n_elec,
            rows_fact_registre=n_inst,
            rows_fact_worldbank=n_wb,
            duration_seconds=duration,
        )
    except Exception as e:
        logger.error(f"[Gold Loader] Échec du chargement Gold : {e}", exc_info=True)
        return GoldLoadReport(
            status="FAILED",
            duration_seconds=round(time.time() - start_time, 2),
            errors=[str(e)],
        )


if __name__ == "__main__":
    report = load_silver_to_gold()
    print("=" * 60)
    print("BILAN DU CHARGEMENT GOLD POSTGRESQL")
    print("=" * 60)
    print(f"Statut                  : {report.status}")
    print(f"Durée totale            : {report.duration_seconds} s")
    print(f"gold.dim_temps          : {report.rows_dim_temps:,} lignes")
    print(f"gold.dim_geographie     : {report.rows_dim_geographie:,} lignes")
    print(f"gold.fact_electricite   : {report.rows_fact_electricite:,} lignes")
    print(f"gold.fact_registre      : {report.rows_fact_registre:,} lignes")
    print(f"gold.fact_worldbank     : {report.rows_fact_worldbank:,} lignes")
    if report.errors:
        print(f"Erreurs rencontrées     : {report.errors}")
    print("=" * 60)
