"""Module d'ingestion du Registre National des installations de production et de stockage (Enedis / RTE / ELD).

Ce module télécharge de façon résiliente le registre national au millésime officiel du 31/12/2025,
calcule son empreinte d'intégrité SHA-256, extrait ses métadonnées structurelles et archive
le flux brut de manière immuable dans la couche Bronze (data/raw/enedis/).
"""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import List, Optional

import requests

from config.settings import settings
from src.energy_observatory.ingestion.rte import inspect_csv_file
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class EnedisIngestionResult:
    """Résultat structuré de l'ingestion du registre national Enedis (Bronze)."""

    status: str  # "SUCCESS", "FAILED", "SKIPPED_ALREADY_EXISTS"
    source_name: str
    millesime: str
    source_url: str
    raw_file_path: Optional[Path]
    metadata_file_path: Optional[Path]
    file_size_bytes: int
    sha256_hash: Optional[str]
    row_count: int
    columns: List[str]
    collected_at: str
    duration_seconds: float
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Sérialise le résultat en dictionnaire JSON-compatible."""
        data = asdict(self)
        if self.raw_file_path:
            data["raw_file_path"] = str(self.raw_file_path)
        if self.metadata_file_path:
            data["metadata_file_path"] = str(self.metadata_file_path)
        return data


def ingest_enedis_registre_bronze(
    target_dir: Optional[Path] = None,
    force_download: bool = False,
    timeout: Optional[int] = None,
    chunk_size: Optional[int] = None,
) -> EnedisIngestionResult:
    """Télécharge et archive le flux brut du registre national (millésime 31/12/2025) dans Bronze.

    Args:
        target_dir: Répertoire de destination (défaut : settings.ENEDIS_RAW_DIR).
        force_download: Si True, force le téléchargement même si le fichier existe déjà.
        timeout: Délai d'attente HTTP en secondes (défaut : settings.HTTP_TIMEOUT_SECONDS).
        chunk_size: Taille des blocs de streaming en octets (défaut : settings.HTTP_CHUNK_SIZE_BYTES).

    Returns:
        EnedisIngestionResult: Rapport d'ingestion détaillé.
    """
    start_time = time.time()
    collected_at = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    millesime = "2025-12-31"

    dest_dir = target_dir or settings.ENEDIS_RAW_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    csv_filename = f"enedis_registre_2025_{date_str}.csv"
    meta_filename = f"enedis_registre_2025_{date_str}_metadata.json"

    raw_file_path = dest_dir / csv_filename
    metadata_file_path = dest_dir / meta_filename
    temp_file_path = dest_dir / f"{csv_filename}.tmp"

    source_url = settings.ENEDIS_REGISTRE_CSV_URL
    http_timeout = timeout or settings.HTTP_TIMEOUT_SECONDS
    stream_chunk_size = chunk_size or settings.HTTP_CHUNK_SIZE_BYTES

    # 1. Vérification d'idempotence
    if raw_file_path.exists() and metadata_file_path.exists() and not force_download:
        file_size = raw_file_path.stat().st_size
        if file_size > 0:
            logger.info(
                f"[Enedis Ingestion] Fichier déjà présent ({csv_filename}, {file_size / (1024*1024):.2f} Mo). "
                f"Ingestion ignorée (utiliser force_download=True pour écraser)."
            )
            row_count, columns = inspect_csv_file(raw_file_path)
            duration = round(time.time() - start_time, 2)
            return EnedisIngestionResult(
                status="SKIPPED_ALREADY_EXISTS",
                source_name="ENEDIS_REGISTRE_INSTALLATIONS",
                millesime=millesime,
                source_url=source_url,
                raw_file_path=raw_file_path,
                metadata_file_path=metadata_file_path,
                file_size_bytes=file_size,
                sha256_hash=None,
                row_count=row_count,
                columns=columns,
                collected_at=collected_at,
                duration_seconds=duration,
            )

    logger.info(f"[Enedis Ingestion] Démarrage du téléchargement depuis : {source_url}")
    hasher = hashlib.sha256()
    total_bytes = 0

    try:
        # 2. Requête en streaming
        with requests.get(
            source_url,
            stream=True,
            timeout=http_timeout,
            headers={"User-Agent": "Observatoire-Energetique-FR/0.1.0"},
        ) as response:
            response.raise_for_status()

            with open(temp_file_path, mode="wb") as f_out:
                for chunk in response.iter_content(chunk_size=stream_chunk_size):
                    if chunk:
                        f_out.write(chunk)
                        hasher.update(chunk)
                        total_bytes += len(chunk)
                        if total_bytes % (10 * 1024 * 1024) == 0:
                            logger.info(
                                f"[Enedis Ingestion] En cours : {total_bytes / (1024*1024):.1f} Mo reçus..."
                            )

        # 3. Validation et déplacement atomique
        if total_bytes == 0:
            raise ValueError("Le fichier téléchargé est vide (0 octet).")

        temp_file_path.replace(raw_file_path)
        sha256_digest = hasher.hexdigest()
        logger.info(
            f"[Enedis Ingestion] Téléchargement terminé : {total_bytes / (1024*1024):.2f} Mo. "
            f"SHA-256: {sha256_digest}"
        )

        # 4. Inspection structurelle du CSV
        row_count, columns = inspect_csv_file(raw_file_path)
        duration = round(time.time() - start_time, 2)
        logger.info(
            f"[Enedis Ingestion] Installations recensées : {row_count:,} | Colonnes : {len(columns)}"
        )

        # 5. Écriture du fichier de métadonnées sidecar
        result = EnedisIngestionResult(
            status="SUCCESS",
            source_name="ENEDIS_REGISTRE_INSTALLATIONS",
            millesime=millesime,
            source_url=source_url,
            raw_file_path=raw_file_path,
            metadata_file_path=metadata_file_path,
            file_size_bytes=total_bytes,
            sha256_hash=sha256_digest,
            row_count=row_count,
            columns=columns,
            collected_at=collected_at,
            duration_seconds=duration,
        )

        with open(metadata_file_path, mode="w", encoding="utf-8") as f_meta:
            json.dump(result.to_dict(), f_meta, indent=2, ensure_ascii=False)

        logger.info(f"[Enedis Ingestion] Métadonnées enregistrées dans {metadata_file_path}")
        return result

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Erreur réseau lors du téléchargement : {req_err}"
        logger.error(f"[Enedis Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return EnedisIngestionResult(
            status="FAILED",
            source_name="ENEDIS_REGISTRE_INSTALLATIONS",
            millesime=millesime,
            source_url=source_url,
            raw_file_path=None,
            metadata_file_path=None,
            file_size_bytes=0,
            sha256_hash=None,
            row_count=0,
            columns=[],
            collected_at=collected_at,
            duration_seconds=round(time.time() - start_time, 2),
            error_message=error_msg,
        )
    except Exception as exc:
        error_msg = f"Erreur inattendue : {exc}"
        logger.error(f"[Enedis Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return EnedisIngestionResult(
            status="FAILED",
            source_name="ENEDIS_REGISTRE_INSTALLATIONS",
            millesime=millesime,
            source_url=source_url,
            raw_file_path=None,
            metadata_file_path=None,
            file_size_bytes=0,
            sha256_hash=None,
            row_count=0,
            columns=[],
            collected_at=collected_at,
            duration_seconds=round(time.time() - start_time, 2),
            error_message=error_msg,
        )


def main():
    """Point d'entrée CLI pour lancer l'ingestion Enedis manuellement."""
    parser = argparse.ArgumentParser(
        description="Ingestion du registre national des installations (Couche Bronze)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force le retéléchargement même si le fichier brut du jour existe déjà.",
    )
    args = parser.parse_args()

    logger.info("=== Lancement de l'ingestion Registre National Enedis (au 31/12/2025) ===")
    result = ingest_enedis_registre_bronze(force_download=args.force)

    print("\n--- Rapport d'ingestion Registre National ---")
    print(f"Statut : {result.status}")
    print(f"Source : {result.source_name}")
    print(f"Millésime : {result.millesime}")
    print(f"Fichier brut : {result.raw_file_path}")
    print(f"Taille : {result.file_size_bytes / (1024*1024):.2f} Mo")
    print(f"SHA-256 : {result.sha256_hash}")
    print(f"Nombre de lignes : {result.row_count:,}")
    print(f"Nombre de colonnes : {len(result.columns)}")
    print(f"Durée : {result.duration_seconds} s")
    if result.error_message:
        print(f"Erreur : {result.error_message}")


if __name__ == "__main__":
    main()
