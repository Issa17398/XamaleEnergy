"""Tests unitaires pour la couche Silver (Transformation, Nettoyage, Parquet)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from src.energy_observatory.transformation.cleaning import (
    TransformationResult,
    clean_column_name,
)
from src.energy_observatory.transformation.enedis_transform import (
    transform_enedis_registre_bronze_to_silver,
)
from src.energy_observatory.transformation.rte_transform import (
    transform_rte_national_bronze_to_silver,
)
from src.energy_observatory.transformation.world_bank_transform import (
    transform_world_bank_bronze_to_silver,
)


class TestCleaningUtils:
    """Tests du nettoyage des noms de colonnes et utilitaires."""

    def test_clean_column_name_accents_and_units(self):
        assert clean_column_name("Périmètre") == "perimetre"
        assert clean_column_name("Consommation (MW)") == "consommation_mw"
        assert clean_column_name("Prévision J-1 (MW)") == "prevision_j1_mw"
        assert clean_column_name("Taux de CO2 (g/kWh)") == "taux_co2_g_kwh"
        assert clean_column_name("Hydraulique - Fil de l'eau + éclusée (MW)") == "hydraulique_fil_de_l_eau_eclusee_mw"

    def test_clean_column_name_enedis_mappings(self):
        assert clean_column_name("codeEICResourceObject") == "code_eic"
        assert clean_column_name("puisMaxInstallee") == "puis_max_installee_kw"
        assert clean_column_name("dateMiseEnservice (format date)") == "date_mise_en_service_iso"
        assert clean_column_name("maxPuis") == "max_puis_kw"


class TestRteTransformation:
    """Tests de transformation RTE éCO2mix."""

    def test_rte_silver_transform_filters_forecasts_and_exports_parquet(self, tmp_path: Path):
        # Création d'un mock CSV Bronze RTE
        mock_csv = tmp_path / "rte_bronze_mock.csv"
        csv_content = (
            "Périmètre;Nature;Date;Heure;Date - Heure;Consommation (MW);Prévision J-1 (MW);Prévision J (MW);Nucléaire (MW);Éolien (MW);Solaire (MW);Hydraulique (MW);Gaz (MW);Charbon (MW);Fioul (MW);Bioénergies (MW);Taux de CO2 (g/kWh)\n"
            # Ligne 1 : Pas 30 min valide
            "France;Données définitives;2024-01-01;00:00;2024-01-01T00:00:00+01:00;55000;54500;54800;42000;3000;0;5000;2500;0;100;1000;45\n"
            # Ligne 2 : Pas 15 min (prévision seule, consommation vide) -> Doit être ignorée de la série 30 min
            "France;Données définitives;2024-01-01;00:15;2024-01-01T00:15:00+01:00;;54300;54600;;;;;;;;;\n"
            # Ligne 3 : Pas 30 min valide
            "France;Données définitives;2024-01-01;00:30;2024-01-01T00:30:00+01:00;54000;53900;54100;41500;3100;0;5000;2400;0;100;1000;44\n"
            # Ligne 4 : Pas 30 min anomalie (consommation <= 0) -> Doit être rejetée
            "France;Données définitives;2024-01-01;01:00;2024-01-01T01:00:00+01:00;-10;50000;50000;40000;2000;0;5000;2000;0;0;1000;40\n"
        )
        mock_csv.write_text(csv_content, encoding="utf-8")

        out_dir = tmp_path / "silver"
        rej_dir = tmp_path / "rejected"

        result = transform_rte_national_bronze_to_silver(
            bronze_file=mock_csv,
            output_dir=out_dir,
            rejected_dir=rej_dir,
        )

        assert result.status == "SUCCESS"
        assert result.total_input_rows == 4
        assert result.valid_output_rows == 2
        assert result.rejected_rows == 1

        # Vérification du fichier Parquet produit
        parquet_file = Path(result.silver_output_path)
        assert parquet_file.exists()
        df_silver = pd.read_parquet(parquet_file)
        assert len(df_silver) == 2
        assert "consommation_mw" in df_silver.columns
        assert "date_heure" in df_silver.columns
        assert df_silver["consommation_mw"].tolist() == [55000.0, 54000.0]

        # Vérification du rejet
        assert result.rejected_output_path is not None
        assert Path(result.rejected_output_path).exists()


class TestEnedisTransformation:
    """Tests de transformation Registre National Enedis."""

    def test_enedis_silver_transform_preserves_strings_and_handles_rejections(self, tmp_path: Path):
        mock_csv = tmp_path / "enedis_bronze_mock.csv"
        csv_content = (
            "nomInstallation;codeEICResourceObject;codeINSEECommune;commune;codeDepartement;codeRegion;dateRaccordement;dateMiseEnService;puisMaxInstallee;filiere;dateMiseEnservice (format date)\n"
            # Ligne 1 : Valide avec département commençant par 0 ("01" Ain)
            "Ferme Solaire 1;17W001;01001;Amberieu;01;84;15/06/2020;15/06/2020;250.5;Solaire;2020-06-15\n"
            # Ligne 2 : Valide en Corse ("2A")
            "Eolien Corse;17W002;2A001;Afa;2A;94;20/09/2018;20/09/2018;1200.0;Eolien;2018-09-20\n"
            # Ligne 3 : Rejet capacité négative (-50)
            "Installation Anormale;;75001;Paris;75;11;01/01/2021;01/01/2021;-50.0;Solaire;2021-01-01\n"
            # Ligne 4 : Rejet filière vide
            "Installation Sans Filiere;;13001;Marseille;13;93;01/01/2021;01/01/2021;100.0;;2021-01-01\n"
        )
        mock_csv.write_text(csv_content, encoding="utf-8")

        out_dir = tmp_path / "silver"
        rej_dir = tmp_path / "rejected"

        result = transform_enedis_registre_bronze_to_silver(
            bronze_file=mock_csv,
            output_dir=out_dir,
            rejected_dir=rej_dir,
        )

        assert result.status == "SUCCESS"
        assert result.total_input_rows == 4
        assert result.valid_output_rows == 2
        assert result.rejected_rows == 2

        # Vérification Parquet
        parquet_file = Path(result.silver_output_path)
        assert parquet_file.exists()
        df_silver = pd.read_parquet(parquet_file)
        assert len(df_silver) == 2
        # Vérification que le département '01' est resté une chaîne et n'est pas devenu l'entier 1
        assert df_silver["code_departement"].tolist() == ["01", "2A"]
        assert df_silver["puis_max_installee_kw"].tolist() == [250.5, 1200.0]


class TestWorldBankTransformation:
    """Tests de transformation Banque Mondiale."""

    def test_world_bank_silver_transform_preserves_missing_and_validates(self, tmp_path: Path):
        mock_json = tmp_path / "worldbank_bronze_mock.json"
        raw_payload = [
            {"page": 1, "pages": 1, "per_page": 10, "total": 4},
            [
                # Ligne 1 : Année 2024, valeur 100
                {
                    "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity"},
                    "country": {"id": "FR", "value": "France"},
                    "countryiso3code": "FRA",
                    "date": "2024",
                    "value": 100,
                },
                # Ligne 2 : Année 2025, valeur nulle (doit être préservée avec is_missing=True)
                {
                    "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity"},
                    "country": {"id": "FR", "value": "France"},
                    "countryiso3code": "FRA",
                    "date": "2025",
                    "value": None,
                },
                # Ligne 3 : Année 2020, valeur 99.8
                {
                    "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity"},
                    "country": {"id": "FR", "value": "France"},
                    "countryiso3code": "FRA",
                    "date": "2020",
                    "value": 99.8,
                },
                # Ligne 4 : Rejet valeur > 100% (150%)
                {
                    "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity"},
                    "country": {"id": "FR", "value": "France"},
                    "countryiso3code": "FRA",
                    "date": "2019",
                    "value": 150.0,
                },
            ],
        ]
        mock_json.write_text(json.dumps(raw_payload), encoding="utf-8")

        out_dir = tmp_path / "silver"
        rej_dir = tmp_path / "rejected"

        result = transform_world_bank_bronze_to_silver(
            bronze_file=mock_json,
            output_dir=out_dir,
            rejected_dir=rej_dir,
        )

        assert result.status == "SUCCESS"
        assert result.total_input_rows == 4
        assert result.valid_output_rows == 3
        assert result.rejected_rows == 1

        # Vérification Parquet
        parquet_file = Path(result.silver_output_path)
        assert parquet_file.exists()
        df_silver = pd.read_parquet(parquet_file)
        assert len(df_silver) == 3
        # Doit être trié chronologiquement ascendant (2020, 2024, 2025)
        assert df_silver["year"].tolist() == [2020, 2024, 2025]
        assert df_silver.loc[df_silver["year"] == 2025, "is_missing"].iloc[0] == True
        assert df_silver.loc[df_silver["year"] == 2024, "valeur_pct"].iloc[0] == 100.0
