"""Gestionnaire de connexion et initialisation de la base de données PostgreSQL."""

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from config.settings import settings
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)

# Cache de l'instance d'engine
_ENGINE: Optional[Engine] = None


def get_engine(db_url: Optional[str] = None, echo: bool = False) -> Engine:
    """Crée ou retourne l'instance de moteur SQLAlchemy pour PostgreSQL.

    Args:
        db_url: URL de connexion complète (défaut : settings.database_url).
        echo: Active le logging SQL verbeux si True.

    Returns:
        Engine: Moteur SQLAlchemy configuré avec pool_pre_ping.
    """
    global _ENGINE
    url = db_url or settings.database_url

    if _ENGINE is None or db_url is not None:
        engine_instance = create_engine(
            url,
            pool_pre_ping=True,
            echo=echo,
            future=True,
        )
        if db_url is None:
            _ENGINE = engine_instance
        return engine_instance

    return _ENGINE


def check_connection(engine: Optional[Engine] = None) -> bool:
    """Vérifie la connectivité à PostgreSQL en exécutant 'SELECT 1'.

    Args:
        engine: Engine SQLAlchemy à tester (défaut : get_engine()).

    Returns:
        bool: True si la connexion est établie, False sinon.
    """
    eng = engine or get_engine()
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return True
    except OperationalError as e:
        logger.warning(f"Impossible de se connecter à PostgreSQL : {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue lors du test de connexion PostgreSQL : {e}")
        return False


def init_database(
    engine: Optional[Engine] = None,
    sql_init_dir: Optional[Path] = None,
) -> None:
    """Initialise les schémas, tables et vues dans PostgreSQL à partir des scripts SQL.

    Args:
        engine: Engine SQLAlchemy d'exécution.
        sql_init_dir: Répertoire contenant les scripts .sql (défaut : BASE_DIR / 'sql' / 'init').
    """
    eng = engine or get_engine()
    scripts_dir = sql_init_dir or (settings.BASE_DIR / "sql" / "init")

    if not scripts_dir.exists():
        raise FileNotFoundError(f"Le dossier des scripts SQL {scripts_dir} est introuvable.")

    sql_files = sorted(scripts_dir.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"Aucun script .sql trouvé dans {scripts_dir}.")

    logger.info(f"Initialisation de la base PostgreSQL via {len(sql_files)} scripts...")

    with eng.begin() as conn:
        for sql_file in sql_files:
            logger.info(f"Exécution du script : {sql_file.name}")
            content = sql_file.read_text(encoding="utf-8")
            # Exécution directe des instructions du script
            conn.execute(text(content))

    logger.info("Initialisation de la base PostgreSQL terminée avec succès.")
