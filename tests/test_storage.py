"""Tests unitaires et de validation pour le module de stockage PostgreSQL et Couche Gold."""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from config.settings import settings
from src.energy_observatory.storage.db import get_engine, init_database
from src.energy_observatory.storage.load_gold import (
    _map_filiere_code,
    load_dim_temps,
    load_dim_geographie,
    load_fact_worldbank,
    load_silver_to_gold,
)


def test_settings_database_url():
    """Vérifie la génération correcte de l'URI SQLAlchemy pour PostgreSQL."""
    url = settings.database_url
    assert url.startswith("postgresql+psycopg2://")
    assert f":{settings.POSTGRES_PORT}/" in url
    assert settings.POSTGRES_DB in url


def test_sql_init_scripts_presence_and_structure():
    """Vérifie la présence et le contenu des 4 scripts d'initialisation SQL."""
    init_dir = settings.BASE_DIR / "sql" / "init"
    assert init_dir.exists()

    expected_scripts = [
        "01_create_schemas.sql",
        "02_create_dimensions.sql",
        "03_create_fact_tables.sql",
        "04_create_views_analytics.sql",
    ]

    for script_name in expected_scripts:
        file_path = init_dir / script_name
        assert file_path.exists(), f"Le script {script_name} est manquant."
        content = file_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 50


def test_map_filiere_code():
    """Valide la standardisation taxonomique des filières Enedis vers dim_filiere."""
    assert _map_filiere_code("Solaire Photovoltaïque") == "solaire"
    assert _map_filiere_code("Éolien terrestre") == "eolien"
    assert _map_filiere_code("Hydraulique fil de l'eau") == "hydraulique"
    assert _map_filiere_code("Biomasse agricole") == "bioenergies"
    assert _map_filiere_code("Nucléaire REP") == "nucleaire"
    assert _map_filiere_code("Gaz naturel") == "gaz"
    assert _map_filiere_code("Batterie Li-ion") == "stockage"
    assert _map_filiere_code(None) == "autre"
    assert _map_filiere_code("") == "autre"


def test_dim_temps_feature_engineering(tmp_path):
    """Vérifie la génération calendaire de gold.dim_temps (saisons, jours fériés, noms FR)."""
    # Création d'un mini Parquet RTE de test
    test_parquet = tmp_path / "test_rte.parquet"
    df = pd.DataFrame({
        "date_heure": pd.to_datetime([
            "2024-01-01 00:00:00+00:00",  # Jour de l'An (Férié, Hiver)
            "2024-07-14 12:00:00+00:00",  # Fête Nationale (Férié, Été, Dimanche)
            "2024-04-10 08:30:00+00:00",  # Printemps, Mercredi
        ])
    })
    df.to_parquet(test_parquet)

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_engine.raw_connection.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    with patch("src.energy_observatory.storage.load_gold._fast_copy_df") as mock_copy:
        mock_copy.return_value = 3
        count = load_dim_temps(rte_parquet_path=test_parquet, engine=mock_engine)
        assert count == 3

        # Vérification du DataFrame passé à _fast_copy_df
        passed_df = mock_copy.call_args[0][0]
        assert "date_heure" in passed_df.columns
        assert "saison" in passed_df.columns
        assert "mois_nom" in passed_df.columns
        assert "jour_semaine_nom" in passed_df.columns

        # Ligne 1 : 1er Janvier -> Hiver, Jour férié
        row_jan = passed_df.iloc[0]
        assert row_jan["saison"] == "Hiver"
        assert row_jan["mois_nom"] == "Janvier"
        assert bool(row_jan["est_jour_ferie"]) is True

        # Ligne 2 : 10 Avril -> Printemps, Mercredi
        row_apr = passed_df.iloc[1]
        assert row_apr["saison"] == "Printemps"
        assert row_apr["jour_semaine_nom"] == "Mercredi"
        assert bool(row_apr["est_weekend"]) is False
        assert bool(row_apr["est_jour_ferie"]) is False

        # Ligne 3 : 14 Juillet -> Été, Dimanche (weekend), Jour férié
        row_jul = passed_df.iloc[2]
        assert row_jul["saison"] == "Été"
        assert row_jul["jour_semaine_nom"] == "Dimanche"
        assert bool(row_jul["est_weekend"]) is True
        assert bool(row_jul["est_jour_ferie"]) is True


def test_load_fact_worldbank(tmp_path):
    """Vérifie l'ingestion de la table de faits Banque Mondiale."""
    test_parquet = tmp_path / "test_wb.parquet"
    df = pd.DataFrame({
        "year": [2020, 2021],
        "country_iso3": ["FRA", "FRA"],
        "country_name": ["France", "France"],
        "indicator_id": ["EG.ELC.ACCS.ZS", "EG.ELC.ACCS.ZS"],
        "valeur_pct": [100.0, 100.0],
        "is_missing": [False, False],
    })
    df.to_parquet(test_parquet)

    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = MagicMock()

    with patch("src.energy_observatory.storage.load_gold._fast_copy_df", return_value=2):
        count = load_fact_worldbank(worldbank_parquet_path=test_parquet, engine=mock_engine)
        assert count == 2


def test_load_silver_to_gold_orchestration():
    """Valide l'orchestration complète de load_silver_to_gold avec reporting."""
    mock_engine = MagicMock()

    with patch("src.energy_observatory.storage.load_gold.init_database"), \
         patch("src.energy_observatory.storage.load_gold.load_dim_temps", return_value=100), \
         patch("src.energy_observatory.storage.load_gold.load_dim_geographie", return_value=50), \
         patch("src.energy_observatory.storage.load_gold.load_fact_electricite_national_30min", return_value=100), \
         patch("src.energy_observatory.storage.load_gold.load_fact_registre_installations", return_value=200), \
         patch("src.energy_observatory.storage.load_gold.load_fact_worldbank", return_value=66):

        report = load_silver_to_gold(engine=mock_engine)

        assert report.status == "SUCCESS"
        assert report.rows_dim_temps == 100
        assert report.rows_dim_geographie == 50
        assert report.rows_fact_electricite == 100
        assert report.rows_fact_registre == 200
        assert report.rows_fact_worldbank == 66
        assert report.duration_seconds >= 0.0
