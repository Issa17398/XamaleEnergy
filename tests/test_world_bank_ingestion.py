"""Tests automatisés pour l'ingestion de la Banque Mondiale (Couche Bronze)."""

import json
from pathlib import Path
import pytest
import responses

from src.energy_observatory.ingestion.world_bank import (
    ingest_world_bank_bronze,
    inspect_world_bank_payload,
)

SAMPLE_WORLDBANK_PAYLOAD = [
    {
        "page": 1,
        "pages": 1,
        "per_page": 1000,
        "total": 3,
        "sourceid": "2",
        "lastupdated": "2026-10-08",
    },
    [
        {
            "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity (% of population)"},
            "country": {"id": "FR", "value": "France"},
            "countryiso3code": "FRA",
            "date": "2024",
            "value": 100.0,
            "unit": "",
            "obs_status": "",
            "decimal": 1,
        },
        {
            "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity (% of population)"},
            "country": {"id": "FR", "value": "France"},
            "countryiso3code": "FRA",
            "date": "2023",
            "value": 100.0,
            "unit": "",
            "obs_status": "",
            "decimal": 1,
        },
        {
            "indicator": {"id": "EG.ELC.ACCS.ZS", "value": "Access to electricity (% of population)"},
            "country": {"id": "FR", "value": "France"},
            "countryiso3code": "FRA",
            "date": "1960",
            "value": None,  # Valeur manquante préservée
            "unit": "",
            "obs_status": "",
            "decimal": 1,
        },
    ],
]


def test_inspect_world_bank_payload():
    """Vérifie la détection des métadonnées, observations valides et valeurs nulles."""
    ind_id, ind_name, total, valid, missing, min_y, max_y = inspect_world_bank_payload(
        SAMPLE_WORLDBANK_PAYLOAD
    )
    assert ind_id == "EG.ELC.ACCS.ZS"
    assert "Access to electricity" in ind_name
    assert total == 3
    assert valid == 2
    assert missing == 1
    assert min_y == "1960"
    assert max_y == "2024"


@responses.activate
def test_ingest_world_bank_success_with_mock(tmp_path: Path):
    """Vérifie le téléchargement JSON complet, le hash SHA-256 et la préservation des nulls."""
    url = "https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000"
    responses.add(
        responses.GET,
        url,
        json=SAMPLE_WORLDBANK_PAYLOAD,
        status=200,
        content_type="application/json",
    )

    result = ingest_world_bank_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "SUCCESS"
    assert result.country_code == "FRA"
    assert result.indicator_id == "EG.ELC.ACCS.ZS"
    assert result.total_observations == 3
    assert result.valid_observations == 2
    assert result.missing_observations == 1
    assert result.raw_file_path is not None
    assert result.raw_file_path.exists()
    assert result.metadata_file_path is not None
    assert result.metadata_file_path.exists()
    assert result.sha256_hash is not None

    # Contrôle du contenu des métadonnées sidecar
    with open(result.metadata_file_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["missing_observations"] == 1
    assert meta["valid_observations"] == 2
    assert meta["min_year"] == "1960"
    assert meta["max_year"] == "2024"


@responses.activate
def test_ingest_world_bank_http_error(tmp_path: Path):
    """Vérifie la gestion des erreurs HTTP 404/500."""
    url = "https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000"
    responses.add(
        responses.GET,
        url,
        status=404,
    )

    result = ingest_world_bank_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "FAILED"
    assert result.error_message is not None
    assert "404" in result.error_message
    assert result.raw_file_path is None
    assert len(list(tmp_path.iterdir())) == 0


@responses.activate
def test_ingest_world_bank_invalid_structure(tmp_path: Path):
    """Vérifie le rejet d'une réponse API au format non conforme."""
    url = "https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000"
    responses.add(
        responses.GET,
        url,
        json={"error": "message inattendu"},
        status=200,
    )

    result = ingest_world_bank_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "FAILED"
    assert "invalide" in result.error_message


@responses.activate
def test_ingest_world_bank_idempotence(tmp_path: Path):
    """Vérifie que l'ingestion ignore le retéléchargement si le fichier est déjà présent."""
    url = "https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000"
    responses.add(
        responses.GET,
        url,
        json=SAMPLE_WORLDBANK_PAYLOAD,
        status=200,
    )

    # 1er appel : succès
    res1 = ingest_world_bank_bronze(target_dir=tmp_path, force_download=False)
    assert res1.status == "SUCCESS"

    # 2ème appel : sauté (idempotent)
    res2 = ingest_world_bank_bronze(target_dir=tmp_path, force_download=False)
    assert res2.status == "SKIPPED_ALREADY_EXISTS"
    assert res2.total_observations == 3
