"""Module d'ingestion de la Banque Mondiale (Couche Bronze).

Ce module interroge l'API officielle World Bank Open Data pour extraire
les indicateurs macro-énergétiques (taux d'accès à l'électricité),
vérifie la structure JSON, préserve scrupuleusement les valeurs manquantes (null),
calcule l'empreinte SHA-256 et archive le flux brut de manière immuable.
"""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from config.settings import settings
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


@dataclass
class WorldBankIngestionResult:
    """Résultat structuré de l'ingestion de l'API Banque Mondiale."""

    status: str  # "SUCCESS", "FAILED", "SKIPPED_ALREADY_EXISTS"
    indicator_id: str
    indicator_name: str
    country_code: str
    source_url: str
    raw_file_path: Optional[Path]
    metadata_file_path: Optional[Path]
    total_observations: int
    valid_observations: int
    missing_observations: int
    min_year: Optional[str]
    max_year: Optional[str]
    file_size_bytes: int
    sha256_hash: Optional[str]
    duration_seconds: float
    collected_at: str
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Sérialise le résultat en dictionnaire JSON-compatible."""
        data = asdict(self)
        if self.raw_file_path:
            data["raw_file_path"] = str(self.raw_file_path)
        if self.metadata_file_path:
            data["metadata_file_path"] = str(self.metadata_file_path)
        return data


def inspect_world_bank_payload(
    payload: Any,
) -> Tuple[str, str, int, int, int, Optional[str], Optional[str]]:
    """Inspecte et valide la structure de réponse de l'API Banque Mondiale.

    L'API World Bank renvoie une liste à deux éléments :
    [0] Métadonnées de pagination
    [1] Liste des observations annuelles

    Args:
        payload: Données JSON désérialisées de l'API.

    Returns:
        Tuple: (indicator_id, indicator_name, total_obs, valid_obs, missing_obs, min_year, max_year)
    """
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError(
            "Structure de réponse World Bank invalide : une liste de 2 éléments était attendue."
        )

    records: List[Dict[str, Any]] = payload[1]
    if not isinstance(records, list) or len(records) == 0:
        raise ValueError("Aucun enregistrement d'observation trouvé dans la réponse World Bank.")

    total_obs = len(records)
    valid_obs = 0
    missing_obs = 0
    years: List[str] = []

    first_record = records[0]
    indicator_id = first_record.get("indicator", {}).get("id", "UNKNOWN")
    indicator_name = first_record.get("indicator", {}).get("value", "UNKNOWN")

    for item in records:
        year = str(item.get("date", ""))
        if year:
            years.append(year)
        val = item.get("value")
        if val is not None:
            valid_obs += 1
        else:
            missing_obs += 1

    min_year = min(years) if years else None
    max_year = max(years) if years else None

    return indicator_id, indicator_name, total_obs, valid_obs, missing_obs, min_year, max_year


def ingest_world_bank_bronze(
    country: str = "FRA",
    indicator: str = "EG.ELC.ACCS.ZS",
    target_dir: Optional[Path] = None,
    force_download: bool = False,
    timeout: Optional[int] = None,
) -> WorldBankIngestionResult:
    """Interroge l'API Banque Mondiale et enregistre la réponse brute dans la couche Bronze.

    Args:
        country: Code ISO du pays (ex: 'FRA').
        indicator: Identifiant de l'indicateur (ex: 'EG.ELC.ACCS.ZS').
        target_dir: Répertoire de destination (défaut : settings.WORLDBANK_RAW_DIR).
        force_download: Si True, force le téléchargement même si le fichier du jour existe.
        timeout: Délai d'attente HTTP en secondes (défaut : settings.HTTP_TIMEOUT_SECONDS).

    Returns:
        WorldBankIngestionResult: Rapport d'ingestion détaillé.
    """
    start_time = time.time()
    collected_at = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    dest_dir = target_dir or settings.WORLDBANK_RAW_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    json_filename = f"worldbank_{country}_{indicator.replace('.', '_')}_{date_str}.json"
    meta_filename = f"worldbank_{country}_{indicator.replace('.', '_')}_{date_str}_metadata.json"

    raw_file_path = dest_dir / json_filename
    metadata_file_path = dest_dir / meta_filename
    temp_file_path = dest_dir / f"{json_filename}.tmp"

    source_url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=1000"
    http_timeout = timeout or settings.HTTP_TIMEOUT_SECONDS

    # 1. Vérification d'idempotence
    if raw_file_path.exists() and metadata_file_path.exists() and not force_download:
        file_size = raw_file_path.stat().st_size
        if file_size > 0:
            logger.info(
                f"[WorldBank Ingestion] Fichier déjà présent ({json_filename}). "
                f"Ingestion ignorée (utiliser force_download=True pour écraser)."
            )
            with open(raw_file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            ind_id, ind_name, total, valid, missing, min_y, max_y = inspect_world_bank_payload(
                payload
            )
            duration = round(time.time() - start_time, 2)
            return WorldBankIngestionResult(
                status="SKIPPED_ALREADY_EXISTS",
                indicator_id=ind_id,
                indicator_name=ind_name,
                country_code=country,
                source_url=source_url,
                raw_file_path=raw_file_path,
                metadata_file_path=metadata_file_path,
                total_observations=total,
                valid_observations=valid,
                missing_observations=missing,
                min_year=min_y,
                max_year=max_y,
                file_size_bytes=file_size,
                sha256_hash=None,
                duration_seconds=duration,
                collected_at=collected_at,
            )

    logger.info(f"[WorldBank Ingestion] Interrogation de l'API : {source_url}")

    try:
        # 2. Requête HTTP
        response = requests.get(
            source_url,
            timeout=http_timeout,
            headers={"User-Agent": "Observatoire-Energetique-FR/0.1.0"},
        )
        response.raise_for_status()

        raw_bytes = response.content
        if len(raw_bytes) == 0:
            raise ValueError("Réponse vide reçue de l'API Banque Mondiale.")

        # Vérification du format JSON valide
        payload = response.json()
        (
            ind_id,
            ind_name,
            total_obs,
            valid_obs,
            missing_obs,
            min_year,
            max_year,
        ) = inspect_world_bank_payload(payload)

        # 3. Écriture atomique du fichier brut
        sha256_digest = hashlib.sha256(raw_bytes).hexdigest()
        with open(temp_file_path, mode="wb") as f_out:
            f_out.write(raw_bytes)

        temp_file_path.replace(raw_file_path)
        file_size = len(raw_bytes)
        duration = round(time.time() - start_time, 2)

        logger.info(
            f"[WorldBank Ingestion] Succès : {total_obs} observations ({valid_obs} valides, "
            f"{missing_obs} nulls) pour la période {min_year}-{max_year}."
        )

        # 4. Écriture des métadonnées sidecar
        result = WorldBankIngestionResult(
            status="SUCCESS",
            indicator_id=ind_id,
            indicator_name=ind_name,
            country_code=country,
            source_url=source_url,
            raw_file_path=raw_file_path,
            metadata_file_path=metadata_file_path,
            total_observations=total_obs,
            valid_observations=valid_obs,
            missing_observations=missing_obs,
            min_year=min_year,
            max_year=max_year,
            file_size_bytes=file_size,
            sha256_hash=sha256_digest,
            duration_seconds=duration,
            collected_at=collected_at,
        )

        with open(metadata_file_path, mode="w", encoding="utf-8") as f_meta:
            json.dump(result.to_dict(), f_meta, indent=2, ensure_ascii=False)

        logger.info(f"[WorldBank Ingestion] Métadonnées enregistrées dans {metadata_file_path}")
        return result

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Erreur réseau lors de l'appel API : {req_err}"
        logger.error(f"[WorldBank Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return WorldBankIngestionResult(
            status="FAILED",
            indicator_id=indicator,
            indicator_name="UNKNOWN",
            country_code=country,
            source_url=source_url,
            raw_file_path=None,
            metadata_file_path=None,
            total_observations=0,
            valid_observations=0,
            missing_observations=0,
            min_year=None,
            max_year=None,
            file_size_bytes=0,
            sha256_hash=None,
            duration_seconds=round(time.time() - start_time, 2),
            collected_at=collected_at,
            error_message=error_msg,
        )
    except Exception as exc:
        error_msg = f"Erreur de traitement : {exc}"
        logger.error(f"[WorldBank Ingestion] {error_msg}")
        if temp_file_path.exists():
            temp_file_path.unlink()
        return WorldBankIngestionResult(
            status="FAILED",
            indicator_id=indicator,
            indicator_name="UNKNOWN",
            country_code=country,
            source_url=source_url,
            raw_file_path=None,
            metadata_file_path=None,
            total_observations=0,
            valid_observations=0,
            missing_observations=0,
            min_year=None,
            max_year=None,
            file_size_bytes=0,
            sha256_hash=None,
            duration_seconds=round(time.time() - start_time, 2),
            collected_at=collected_at,
            error_message=error_msg,
        )


def main():
    """Point d'entrée CLI pour lancer l'ingestion Banque Mondiale manuellement."""
    parser = argparse.ArgumentParser(
        description="Ingestion des indicateurs Banque Mondiale (Couche Bronze)."
    )
    parser.add_argument(
        "--country",
        default="FRA",
        help="Code ISO 3 lettres du pays (défaut : FRA).",
    )
    parser.add_argument(
        "--indicator",
        default="EG.ELC.ACCS.ZS",
        help="Code de l'indicateur (défaut : EG.ELC.ACCS.ZS).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force le retéléchargement même si le fichier brut existe déjà.",
    )
    args = parser.parse_args()

    logger.info(f"=== Lancement de l'ingestion Banque Mondiale ({args.country} - {args.indicator}) ===")
    result = ingest_world_bank_bronze(
        country=args.country,
        indicator=args.indicator,
        force_download=args.force,
    )

    print("\n--- Rapport d'ingestion Banque Mondiale ---")
    print(f"Statut : {result.status}")
    print(f"Indicateur : {result.indicator_id} ({result.indicator_name})")
    print(f"Pays : {result.country_code}")
    print(f"Fichier brut : {result.raw_file_path}")
    print(f"Taille : {result.file_size_bytes} octets")
    print(f"SHA-256 : {result.sha256_hash}")
    print(f"Total observations : {result.total_observations}")
    print(f"Observations valides : {result.valid_observations}")
    print(f"Observations nulles (manquantes) : {result.missing_observations}")
    print(f"Période couverte : {result.min_year} - {result.max_year}")
    print(f"Durée : {result.duration_seconds} s")
    if result.error_message:
        print(f"Erreur : {result.error_message}")


if __name__ == "__main__":
    main()
