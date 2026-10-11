"""Dépendances injectables pour les routes FastAPI."""

from typing import Generator
from sqlalchemy import Connection
from src.energy_observatory.storage.db import get_engine


def get_db_connection() -> Generator[Connection, None, None]:
    """Fournit une connexion active au pool PostgreSQL pour la durée de la requête."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
