"""Module d'inspection statistique et exploratoire approfondie de la Couche Silver."""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import settings


def inspect_rte_silver() -> None:
    """Affiche les statistiques clés et un échantillon du jeu de données RTE Silver."""
    parquet_path = settings.DATA_PROCESSED_DIR / "silver_rte_national_30min.parquet"
    if not parquet_path.exists():
        print(f"Fichier introuvable : {parquet_path}")
        return

    print("=" * 80)
    print("1. INSPECTION APPROFONDIE : RTE éCO2mix National (Silver - Pas 30 min)")
    print("=" * 80)
    df = pd.read_parquet(parquet_path)

    print(f"\n[Métadonnées Générales]")
    print(f"  - Total d'observations valides : {len(df):,}")
    print(f"  - Nombre de colonnes           : {len(df.columns)}")
    print(f"  - Horodatage minimal           : {df['date_heure'].min()}")
    print(f"  - Horodatage maximal           : {df['date_heure'].max()}")
    print(f"  - Époque temporelle couverte    : du {df['date'].min()} au {df['date'].max()}")

    # Statistiques clés
    cols_stats = [
        "consommation_mw",
        "nucleaire_mw",
        "eolien_mw",
        "solaire_mw",
        "hydraulique_mw",
        "gaz_mw",
        "taux_co2_g_kwh",
    ]
    existing_cols = [c for c in cols_stats if c in df.columns]
    print("\n[Statistiques Descriptives des Grandeurs Majeures (MW et g/kWh)]")
    stats = df[existing_cols].describe().T[["count", "mean", "std", "min", "50%", "max"]]
    stats.rename(columns={"50%": "median"}, inplace=True)
    # Formater les colonnes numériques
    pd.set_option("display.float_format", lambda x: f"{x:,.1f}")
    pd.set_option("display.width", 120)
    pd.set_option("display.max_columns", 10)
    print(stats.to_string())

    print("\n[Extrait des 3 premières observations]")
    display_cols = ["date_heure", "consommation_mw", "nucleaire_mw", "eolien_mw", "solaire_mw", "taux_co2_g_kwh"]
    print(df[display_cols].head(3).to_string(index=False))

    print("\n[Extrait des 3 dernières observations les plus récentes]")
    print(df[display_cols].tail(3).to_string(index=False))


def inspect_enedis_silver() -> None:
    """Affiche les statistiques clés et la répartition des installations Enedis Silver."""
    parquet_path = settings.DATA_PROCESSED_DIR / "silver_enedis_registre_2025.parquet"
    if not parquet_path.exists():
        print(f"Fichier introuvable : {parquet_path}")
        return

    print("\n" + "=" * 80)
    print("2. INSPECTION APPROFONDIE : Enedis Registre National (Silver - 31/12/2025)")
    print("=" * 80)
    df = pd.read_parquet(parquet_path)

    print(f"\n[Métadonnées Générales]")
    print(f"  - Total d'installations        : {len(df):,}")
    print(f"  - Nombre de colonnes           : {len(df.columns)}")
    total_capacity_mw = df["puis_max_installee_kw"].sum() / 1000.0
    print(f"  - Puissance totale raccordée   : {total_capacity_mw:,.1f} MW ({total_capacity_mw / 1000.0:,.2f} GW)")

    print("\n[Répartition de la Capacité Installée par Filière]")
    filiere_stats = (
        df.groupby("filiere")
        .agg(
            nb_installations=("puis_max_installee_kw", "count"),
            puissance_mw=("puis_max_installee_kw", lambda s: s.sum() / 1000.0),
        )
        .sort_values(by="puissance_mw", ascending=False)
    )
    filiere_stats["part_capacite_pct"] = (
        filiere_stats["puissance_mw"] / filiere_stats["puissance_mw"].sum() * 100.0
    )
    print(filiere_stats.to_string())

    print("\n[Top 5 Régions par Capacité Raccordée (MW)]")
    if "region" in df.columns:
        region_stats = (
            df.groupby("region")
            .agg(
                nb_installations=("puis_max_installee_kw", "count"),
                puissance_mw=("puis_max_installee_kw", lambda s: s.sum() / 1000.0),
            )
            .sort_values(by="puissance_mw", ascending=False)
            .head(5)
        )
        print(region_stats.to_string())

    print("\n[Échantillon d'Installations (3 lignes représentatives)]")
    sample_cols = ["nom_installation", "commune", "code_departement", "filiere", "puis_max_installee_kw", "date_mise_en_service_iso"]
    avail_sample = [c for c in sample_cols if c in df.columns]
    print(df[avail_sample].head(3).to_string(index=False))


def inspect_worldbank_silver() -> None:
    """Affiche les observations et l'historique complet de la Banque Mondiale."""
    parquet_path = settings.DATA_PROCESSED_DIR / "silver_worldbank_access_electricity.parquet"
    if not parquet_path.exists():
        print(f"Fichier introuvable : {parquet_path}")
        return

    print("\n" + "=" * 80)
    print("3. INSPECTION APPROFONDIE : Banque Mondiale (Silver - Taux d'accès 1960-2025)")
    print("=" * 80)
    df = pd.read_parquet(parquet_path)

    print(f"\n[Métadonnées Générales]")
    print(f"  - Total d'années historisées  : {len(df)}")
    print(f"  - Plage temporelle             : {df['year'].min()} -> {df['year'].max()}")
    print(f"  - Observations mesurées        : {(~df['is_missing']).sum()} années")
    print(f"  - Observations manquantes      : {df['is_missing'].sum()} années (1960 à 1989)")

    print("\n[Dernières Décennies Disponibles (1990 à 2025)]")
    measured = df[~df["is_missing"]].sort_values("year", ascending=False)
    print(measured[["year", "country_name", "country_iso3", "valeur_pct", "unit"]].head(10).to_string(index=False))


def inspect_rejected_data() -> None:
    """Affiche le contenu et le motif des données mises en quarantaine."""
    rej_files = sorted(settings.DATA_REJECTED_DIR.glob("*.csv"))
    print("\n" + "=" * 80)
    print("4. INSPECTION DE LA QUARANTAINE (data/rejected/)")
    print("=" * 80)
    if not rej_files:
        print("Aucun fichier de rejet présent : 100% des lignes ont été admises.")
        return

    for rf in rej_files:
        df_rej = pd.read_csv(rf, sep=";", low_memory=False)
        print(f"\nFichier : {rf.name}")
        print(f"  - Lignes rejetées : {len(df_rej)}")
        cols = ["date_heure", "consommation_mw", "rejection_reason"]
        disp = [c for c in cols if c in df_rej.columns]
        print(f"  - Échantillon des rejets :\n{df_rej[disp].head(5).to_string(index=False)}")


def main():
    parser = argparse.ArgumentParser(description="Inspection interactive de la Couche Silver.")
    parser.add_argument(
        "--source",
        choices=["all", "rte", "enedis", "worldbank", "rejects"],
        default="all",
        help="Source spécifique à inspecter (défaut: all)",
    )
    args = parser.parse_args()

    if args.source in ("all", "rte"):
        inspect_rte_silver()
    if args.source in ("all", "enedis"):
        inspect_enedis_silver()
    if args.source in ("all", "worldbank"):
        inspect_worldbank_silver()
    if args.source in ("all", "rejects"):
        inspect_rejected_data()
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
