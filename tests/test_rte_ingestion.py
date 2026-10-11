"""Tests automatisés pour le module d'ingestion RTE éCO2mix (Couche Bronze)."""

import json
from pathlib import Path
import pytest
import responses

from config.settings import settings
from src.energy_observatory.ingestion.rte import (
    ingest_rte_national_bronze,
    inspect_csv_file,
)

SAMPLE_CSV_CONTENT = (
    "perimetre;nature;date;heure;date_heure;consommation;nucleaire;eolien;solaire\n"
    "France;Données définitives;2024-01-01;00:00;2024-01-01T00:00:00+01:00;55000;42000;4500;0\n"
    "France;Données définitives;2024-01-01;00:30;2024-01-01T00:30:00+01:00;54000;42000;4400;0\n"
    "France;Données définitives;2024-01-01;01:00;2024-01-01T01:00:00+01:00;53000;41500;4300;0\n"
)


def test_inspect_csv_file(tmp_path: Path):
    """Vérifie le comptage de lignes et l'extraction des colonnes sur un CSV échantillon."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(SAMPLE_CSV_CONTENT, encoding="utf-8")

    row_count, columns = inspect_csv_file(csv_file)
    assert row_count == 3
    assert columns == [
        "perimetre",
        "nature",
        "date",
        "heure",
        "date_heure",
        "consommation",
        "nucleaire",
        "eolien",
        "solaire",
    ]


@responses.activate
def test_ingest_rte_success_with_mock(tmp_path: Path):
    """Vérifie le téléchargement complet en streaming, le SHA-256 et les métadonnées."""
    responses.add(
        responses.GET,
        settings.RTE_NATIONAL_CSV_URL,
        body=SAMPLE_CSV_CONTENT.encode("utf-8"),
        status=200,
        content_type="text/csv",
        stream=True,
    )

    result = ingest_rte_national_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "SUCCESS"
    assert result.raw_file_path is not None
    assert result.raw_file_path.exists()
    assert result.file_size_bytes == len(SAMPLE_CSV_CONTENT.encode("utf-8"))
    assert result.sha256_hash is not None
    assert result.row_count == 3
    assert len(result.columns) == 9

    # Vérification du fichier de métadonnées
    assert result.metadata_file_path is not None
    assert result.metadata_file_path.exists()

    with open(result.metadata_file_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)
    assert meta_dict["status"] == "SUCCESS"
    assert meta_dict["row_count"] == 3
    assert meta_dict["sha256_hash"] == result.sha256_hash


@responses.activate
def test_ingest_rte_http_error(tmp_path: Path):
    """Vérifie la résilience et le nettoyage des fichiers temporaires en cas d'erreur HTTP 500."""
    responses.add(
        responses.GET,
        settings.RTE_NATIONAL_CSV_URL,
        status=500,
    )

    result = ingest_rte_national_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "FAILED"
    assert result.error_message is not None
    assert "500" in result.error_message
    assert result.raw_file_path is None

    # Aucun fichier résiduel .tmp ou .csv ne doit subsister
    files_in_dir = list(tmp_path.iterdir())
    assert len(files_in_dir) == 0


@responses.activate
def test_ingest_rte_idempotence(tmp_path: Path):
    """Vérifie qu'un deuxième appel sans force_download ignore le retéléchargement."""
    responses.add(
        responses.GET,
        settings.RTE_NATIONAL_CSV_URL,
        body=SAMPLE_CSV_CONTENT.encode("utf-8"),
        status=200,
        stream=True,
    )

    # 1er appel : succès et création
    res1 = ingest_rte_national_bronze(target_dir=tmp_path, force_download=False)
    assert res1.status == "SUCCESS"

    # 2ème appel : doit être SKIPPED_ALREADY_EXISTS
    res2 = ingest_rte_national_bronze(target_dir=tmp_path, force_download=False)
    assert res2.status == "SKIPPED_ALREADY_EXISTS"
    assert res2.row_count == 3
