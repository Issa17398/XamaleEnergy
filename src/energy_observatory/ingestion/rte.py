"""Module d'ingestion de la source RTE éCO2mix (Couche Bronze).

Ce module télécharge de façon résiliente le jeu de données éCO2mix national consolidé
et définitif, calcule son empreinte d'intégrité SHA-256, extrait ses métadonnées
structurelles et sauvegarde les fichiers bruts de façon immuable.
"""

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import List, Optional, Tuple

import requests

from config.settings import settings
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class IngestionResult:
    """Résultat structuré d'une opération d'ingestion Bronze."""

    status: str  # "SUCCESS", "FAILED", "SKIPPED_ALREADY_EXISTS"
    source_name: str
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


def inspect_csv_file(file_path: Path) -> Tuple[int, List[str]]:
    """Inspecte un fichier CSV sans charger l'intégralité en mémoire.

    Détecte le délimiteur, extrait les colonnes de l'en-tête et compte le nombre de lignes.

    Args:
        file_path: Chemin vers le fichier CSV.

    Returns:
        Tuple[int, List[str]]: (nombre_de_lignes_de_donnees, liste_des_colonnes)
    """
    columns: List[str] = []
    row_count = 0

    with open(file_path, mode="r", encoding="utf-8-sig", errors="replace") as f:
        # Lire la première ligne pour déterminer le délimiteur et les colonnes
        first_line = f.readline()
        if not first_line:
            return 0, []

        delimiter = ";" if ";" in first_line else ","
        reader = csv.reader([first_line], delimiter=delimiter)
        header = next(reader, [])
        columns = [col.strip().strip('"') for col in header]

        # Compter les lignes restantes par blocs pour optimiser la mémoire
        for line in f:
            if line.strip():
                row_count += 1

    return row_count, columns


def ingest_rte_national_bronze(
    target_dir: Optional[Path] = None,
    force_download: bool = False,
    timeout: Optional[int] = None,
    chunk_size: Optional[int] = None,
) -> IngestionResult:
    """Télécharge et archive le flux brut éCO2mix national dans la couche Bronze.

    Args:
        target_dir: Répertoire de destination (défaut : settings.RTE_RAW_DIR).
        force_download: Si True, force le téléchargement même si le fichier du jour existe.
        timeout: Délai d'attente HTTP en secondes (défaut : settings.HTTP_TIMEOUT_SECONDS).
        chunk_size: Taille des blocs de streaming en octets (défaut : settings.HTTP_CHUNK_SIZE_BYTES).

    Returns:
        IngestionResult: Rapport détaillé de l'ingestion.
    """
    start_time = time.time()
    collected_at = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    dest_dir = target_dir or settings.RTE_RAW_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    csv_filename = f"rte_national_{date_str}.csv"
    meta_filename = f"rte_national_{date_str}_metadata.json"

    raw_file_path = dest_dir / csv_filename
    metadata_file_path = dest_dir / meta_filename
    temp_file_path = dest_dir / f"{csv_filename}.tmp"

    source_url = settings.RTE_NATIONAL_CSV_URL
    http_timeout = timeout or settings.HTTP_TIMEOUT_SECONDS
    stream_chunk_size = chunk_size or settings.HTTP_CHUNK_SIZE_BYTES

    # 1. Vérification d'idempotence (évite les téléchargements inutiles)
    if raw_file_path.exists() and metadata_file_path.exists() and not force_download:
        file_size = raw_file_path.stat().st_size
        if file_size > 0:
            logger.info(
                f"[RTE Ingestion] Fichier déjà présent ({csv_filename}, {file_size / (1024*1024):.2f} Mo). "
                f"Ingestion ignorée (utiliser force_download=True pour écraser)."
            )
            row_count, columns = inspect_csv_file(raw_file_path)
            duration = time.time() - start_time
            return IngestionResult(
                status="SKIPPED_ALREADY_EXISTS",
                source_name="RTE_ECO2MIX_NATIONAL",
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

    logger.info(f"[RTE Ingestion] Démarrage du téléchargement depuis : {source_url}")
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

            # Enregistrement progressif avec calcul du checksum à la volée
            with open(temp_file_path, mode="wb") as f_out:
                for chunk in response.iter_content(chunk_size=stream_chunk_size):
                    if chunk:
                        f_out.write(chunk)
                        hasher.update(chunk)
                        total_bytes += len(chunk)
                        if total_bytes % (10 * 1024 * 1024) == 0:
                            logger.info(
                                f"[RTE Ingestion] En cours : {total_bytes / (1024*1024):.1f} Mo reçus..."
                            )

        # 3. Validation et déplacement atomique
        if total_bytes == 0:
            raise ValueError("Le fichier téléchargé est vide (0 octet).")

        temp_file_path.replace(raw_file_path)
        sha256_digest = hasher.hexdigest()
        logger.info(
            f"[RTE Ingestion] Téléchargement terminé : {total_bytes / (1024*1024):.2f} Mo. "
            f"SHA-256: {sha256_digest}"
        )

        # 4. Inspection structurelle du CSV
        row_count, columns = inspect_csv_file(raw_file_path)
        duration = round(time.time() - start_time, 2)
        logger.info(
            f"[RTE Ingestion] Lignes de données : {row_count:,} | Colonnes détectées : {len(columns)}"
        )

        # 5. Écriture du fichier de métadonnées sidecar
        result = IngestionResult(
            status="SUCCESS",
            source_name="RTE_ECO2MIX_NATIONAL",
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

        logger.info(f"[RTE Ingestion] Métadonnées enregistrées dans {metadata_file_path}")
        return result

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Erreur réseau lors du téléchargement : {req_err}"
        logger.error(f"[RTE Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return IngestionResult(
            status="FAILED",
            source_name="RTE_ECO2MIX_NATIONAL",
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
        logger.error(f"[RTE Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return IngestionResult(
            status="FAILED",
            source_name="RTE_ECO2MIX_NATIONAL",
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
    """Point d'entrée CLI pour lancer l'ingestion RTE manuellement."""
    parser = argparse.ArgumentParser(
        description="Ingestion du flux brut éCO2mix national (Couche Bronze)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force le retéléchargement même si le fichier brut du jour existe déjà.",
    )
    args = parser.parse_args()

    logger.info("=== Lancement de l'ingestion RTE éCO2mix National ===")
    result = ingest_rte_national_bronze(force_download=args.force)

    print("\n--- Rapport d'ingestion ---")
    print(f"Statut : {result.status}")
    print(f"Source : {result.source_name}")
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
