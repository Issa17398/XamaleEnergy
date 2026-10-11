"""Configuration centrale de l'Observatoire Énergétique de la France.

Ce module centralise la gestion des chemins, des variables d'environnement,
des URLs sources et des paramètres d'ingestion/stockage.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, Any

# Chargement optionnel de python-dotenv si disponible
try:
    from dotenv import load_dotenv
    _ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    """Classe de configuration immuable pour le projet."""

    # Chemins de base du projet
    BASE_DIR: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent
    )

    # Environnement et logging
    APP_ENV: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development")
    )
    LOG_LEVEL: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    # Répertoires de données (Architecture Medallion)
    DATA_RAW_DIR: Path = field(init=False)
    DATA_PROCESSED_DIR: Path = field(init=False)
    DATA_REJECTED_DIR: Path = field(init=False)
    DATA_REPORTS_DIR: Path = field(init=False)
    RTE_RAW_DIR: Path = field(init=False)
    ENEDIS_RAW_DIR: Path = field(init=False)
    WORLDBANK_RAW_DIR: Path = field(init=False)

    # URLs Source A - RTE éCO2mix
    RTE_NATIONAL_CSV_URL: str = field(
        default_factory=lambda: os.getenv(
            "RTE_NATIONAL_CSV_URL",
            "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/exports/csv?use_labels=true",
        )
    )
    RTE_NATIONAL_API_URL: str = field(
        default_factory=lambda: os.getenv(
            "RTE_NATIONAL_API_URL",
            "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/records",
        )
    )
    RTE_REGIONAL_CSV_URL: str = field(
        default_factory=lambda: os.getenv(
            "RTE_REGIONAL_CSV_URL",
            "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-regional-cons-def/exports/csv?use_labels=true",
        )
    )

    # URLs Source B - Enedis / Registre National des installations (31/12/2025)
    ENEDIS_REGISTRE_CSV_URL: str = field(
        default_factory=lambda: os.getenv(
            "ENEDIS_REGISTRE_CSV_URL",
            "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/registre-national-installation-production-stockage-electricite-agrege-311225/exports/csv?use_labels=true",
        )
    )

    # URLs Source C - Banque Mondiale
    WORLDBANK_API_URL: str = field(
        default_factory=lambda: os.getenv(
            "WORLDBANK_API_URL",
            "https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000",
        )
    )

    # Paramètres réseau & Ingestion résiliente
    HTTP_TIMEOUT_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))
    )
    HTTP_MAX_RETRIES: int = field(
        default_factory=lambda: int(os.getenv("HTTP_MAX_RETRIES", "3"))
    )
    HTTP_CHUNK_SIZE_BYTES: int = field(
        default_factory=lambda: int(os.getenv("HTTP_CHUNK_SIZE_BYTES", "1048576"))
    )

    # Paramètres PostgreSQL (Phase 7)
    POSTGRES_HOST: str = field(
        default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost")
    )
    POSTGRES_PORT: int = field(
        default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432"))
    )
    POSTGRES_DB: str = field(
        default_factory=lambda: os.getenv("POSTGRES_DB", "energy_db")
    )
    POSTGRES_USER: str = field(
        default_factory=lambda: os.getenv("POSTGRES_USER", "postgres")
    )
    POSTGRES_PASSWORD: str = field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "postgres")
    )

    def __post_init__(self) -> None:
        """Initialise les chemins dérivés relatifs au BASE_DIR."""
        base = self.BASE_DIR
        raw_dir = base / os.getenv("DATA_RAW_DIR", "data/raw")
        proc_dir = base / os.getenv("DATA_PROCESSED_DIR", "data/processed")
        rej_dir = base / os.getenv("DATA_REJECTED_DIR", "data/rejected")
        rep_dir = base / os.getenv("DATA_REPORTS_DIR", "data/reports")

        object.__setattr__(self, "DATA_RAW_DIR", raw_dir)
        object.__setattr__(self, "DATA_PROCESSED_DIR", proc_dir)
        object.__setattr__(self, "DATA_REJECTED_DIR", rej_dir)
        object.__setattr__(self, "DATA_REPORTS_DIR", rep_dir)

        object.__setattr__(self, "RTE_RAW_DIR", raw_dir / "rte")
        object.__setattr__(self, "ENEDIS_RAW_DIR", raw_dir / "enedis")
        object.__setattr__(self, "WORLDBANK_RAW_DIR", raw_dir / "world_bank")

    def ensure_directories(self) -> None:
        """Crée automatiquement les répertoires nécessaires s'ils n'existent pas."""
        for path in [
            self.DATA_RAW_DIR,
            self.DATA_PROCESSED_DIR,
            self.DATA_REJECTED_DIR,
            self.DATA_REPORTS_DIR,
            self.RTE_RAW_DIR,
            self.ENEDIS_RAW_DIR,
            self.WORLDBANK_RAW_DIR,
            self.BASE_DIR / "logs",
        ]:
            path.mkdir(parents=True, exist_ok=True)

    @property
    def database_url(self) -> str:
        """Retourne l'URI de connexion SQLAlchemy à PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Exporte la configuration sous forme de dictionnaire non-sensible."""
        return {
            "APP_ENV": self.APP_ENV,
            "LOG_LEVEL": self.LOG_LEVEL,
            "BASE_DIR": str(self.BASE_DIR),
            "DATA_RAW_DIR": str(self.DATA_RAW_DIR),
            "DATA_PROCESSED_DIR": str(self.DATA_PROCESSED_DIR),
            "DATA_REJECTED_DIR": str(self.DATA_REJECTED_DIR),
            "RTE_NATIONAL_CSV_URL": self.RTE_NATIONAL_CSV_URL,
            "ENEDIS_REGISTRE_CSV_URL": self.ENEDIS_REGISTRE_CSV_URL,
            "WORLDBANK_API_URL": self.WORLDBANK_API_URL,
            "HTTP_TIMEOUT_SECONDS": self.HTTP_TIMEOUT_SECONDS,
            "HTTP_MAX_RETRIES": self.HTTP_MAX_RETRIES,
        }


# Instance singleton utilisable dans toute l'application
settings = Settings()
