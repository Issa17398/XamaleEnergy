"""Tests automatisés pour l'ingestion du Registre National Enedis (Couche Bronze)."""

import json
from pathlib import Path
import pytest
import responses

from config.settings import settings
from src.energy_observatory.ingestion.enedis import ingest_enedis_registre_bronze

SAMPLE_ENEDIS_CSV = (
    "codeeicresourceobject;nominstallation;codeiris;codeinseecommune;commune;departement;region;codefiliere;filiere;technologie;puismaxinstallee;regime\n"
    "17W000001656211B;privé;792010000;79201;Pamproux;Deux-Sèvres;Nouvelle-Aquitaine;SOLAI;Solaire;Photovoltaïque;250.0;En service\n"
    "17W000000484944J;privé;793290107;79329;Thouars;Deux-Sèvres;Nouvelle-Aquitaine;SOLAI;Solaire;Photovoltaïque;156.0;En service\n"
)


@responses.activate
def test_ingest_enedis_success_with_mock(tmp_path: Path):
    """Vérifie le téléchargement complet du registre Enedis avec calcul du hash et métadonnées."""
    responses.add(
        responses.GET,
        settings.ENEDIS_REGISTRE_CSV_URL,
        body=SAMPLE_ENEDIS_CSV.encode("utf-8"),
        status=200,
        content_type="text/csv",
        stream=True,
    )

    result = ingest_enedis_registre_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "SUCCESS"
    assert result.millesime == "2025-12-31"
    assert result.source_name == "ENEDIS_REGISTRE_INSTALLATIONS"
    assert result.raw_file_path is not None
    assert result.raw_file_path.exists()
    assert result.file_size_bytes == len(SAMPLE_ENEDIS_CSV.encode("utf-8"))
    assert result.sha256_hash is not None
    assert result.row_count == 2
    assert len(result.columns) == 12

    # Vérification des métadonnées
    assert result.metadata_file_path is not None
    assert result.metadata_file_path.exists()

    with open(result.metadata_file_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["status"] == "SUCCESS"
    assert meta["millesime"] == "2025-12-31"
    assert meta["row_count"] == 2
    assert meta["sha256_hash"] == result.sha256_hash


@responses.activate
def test_ingest_enedis_http_error(tmp_path: Path):
    """Vérifie la gestion des erreurs réseau et l'absence de fichiers orphelins temporaires."""
    responses.add(
        responses.GET,
        settings.ENEDIS_REGISTRE_CSV_URL,
        status=503,
    )

    result = ingest_enedis_registre_bronze(target_dir=tmp_path, force_download=True)

    assert result.status == "FAILED"
    assert result.error_message is not None
    assert "503" in result.error_message
    assert result.raw_file_path is None

    # Aucun fichier temporaire ne doit subsister
    assert len(list(tmp_path.iterdir())) == 0


@responses.activate
def test_ingest_enedis_idempotence(tmp_path: Path):
    """Vérifie qu'un deuxième appel sans force_download ne retélécharge pas inutilement."""
    responses.add(
        responses.GET,
        settings.ENEDIS_REGISTRE_CSV_URL,
        body=SAMPLE_ENEDIS_CSV.encode("utf-8"),
        status=200,
        stream=True,
    )

    # 1er appel : succès
    res1 = ingest_enedis_registre_bronze(target_dir=tmp_path, force_download=False)
    assert res1.status == "SUCCESS"

    # 2ème appel : doit être ignoré
    res2 = ingest_enedis_registre_bronze(target_dir=tmp_path, force_download=False)
    assert res2.status == "SKIPPED_ALREADY_EXISTS"
    assert res2.row_count == 2
