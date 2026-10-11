"""Tests automatisés pour valider l'environnement, les paramètres et les logs."""

import logging
from pathlib import Path
import pytest

from config.settings import settings
from src.energy_observatory.utils.logging_config import setup_logger


def test_settings_paths():
    """Vérifie que les chemins de configuration sont valides et cohérents."""
    assert settings.BASE_DIR.exists()
    assert (settings.BASE_DIR / "pyproject.toml").exists()

    # Les répertoires de données doivent être bien dérivés
    assert settings.DATA_RAW_DIR == settings.BASE_DIR / "data" / "raw"
    assert settings.DATA_PROCESSED_DIR == settings.BASE_DIR / "data" / "processed"
    assert settings.DATA_REJECTED_DIR == settings.BASE_DIR / "data" / "rejected"

    assert settings.RTE_RAW_DIR == settings.DATA_RAW_DIR / "rte"
    assert settings.ENEDIS_RAW_DIR == settings.DATA_RAW_DIR / "enedis"
    assert settings.WORLDBANK_RAW_DIR == settings.DATA_RAW_DIR / "world_bank"


def test_settings_ensure_directories():
    """Vérifie que ensure_directories crée bien tous les dossiers nécessaires."""
    settings.ensure_directories()
    assert settings.RTE_RAW_DIR.exists()
    assert settings.ENEDIS_RAW_DIR.exists()
    assert settings.WORLDBANK_RAW_DIR.exists()
    assert settings.DATA_PROCESSED_DIR.exists()
    assert settings.DATA_REJECTED_DIR.exists()
    assert (settings.BASE_DIR / "logs").exists()


def test_settings_urls_configured():
    """Vérifie que les URLs des 3 sources sont bien définies et sécurisées (HTTPS)."""
    assert settings.RTE_NATIONAL_CSV_URL.startswith("https://")
    assert settings.RTE_NATIONAL_API_URL.startswith("https://")
    assert settings.ENEDIS_REGISTRE_CSV_URL.startswith("https://")
    assert settings.WORLDBANK_API_URL.startswith("https://")


def test_logger_setup():
    """Vérifie que le logger est configuré correctement et écrit sans erreur."""
    logger = setup_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
    assert len(logger.handlers) >= 1

    # Test d'émission de logs
    logger.info("Test de log INFO réussi")
    logger.debug("Test de log DEBUG")

    # Idempotence : un deuxième appel ne duplique pas les handlers
    initial_handler_count = len(logger.handlers)
    logger2 = setup_logger("test_module")
    assert len(logger2.handlers) == initial_handler_count
