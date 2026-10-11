"""Configuration centralisée des logs pour l'Observatoire Énergétique.

Fournit des logs formatés, horodatés, avec niveau de log configurable,
affichés sur la console standard et persistés dans logs/energy_observatory.log.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional

from config.settings import settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """Configure et retourne un logger standardisé pour le projet.

    Args:
        name: Nom du logger (généralement __name__). Si None, retourne le logger racine du projet.

    Returns:
        logging.Logger: Instance de logger configurée.
    """
    logger_name = name or "energy_observatory"
    logger = logging.getLogger(logger_name)

    # Récupération du niveau de log configuré
    log_level_str = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Évite l'accumulation de doublons de handlers si setup_logger est appelé plusieurs fois
    if logger.handlers:
        return logger

    # Format standardisé : Horodatage - Niveau - Module - Message
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Handler Console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Handler Fichier tournant (logs/energy_observatory.log)
    try:
        logs_dir = settings.BASE_DIR / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=logs_dir / "energy_observatory.log",
            maxBytes=5 * 1024 * 1024,  # 5 Mo par fichier
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        # En cas d'impossibilité d'écrire sur le disque, on continue avec la console
        logger.warning(
            f"Impossible d'initialiser le fichier de log dans {logs_dir}: {exc}"
        )

    # Ne propage pas au logger root par défaut pour éviter des affichages dupliqués
    logger.propagate = False

    return logger
