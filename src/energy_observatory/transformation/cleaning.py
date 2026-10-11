"""Utilitaires de nettoyage et normalisation des données (Couche Silver)."""

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import unicodedata

import pandas as pd


@dataclass
class TransformationResult:
    """Résultat structuré d'un traitement de transformation Silver."""

    status: str  # "SUCCESS", "FAILED"
    source_name: str
    bronze_input_path: str
    silver_output_path: str
    rejected_output_path: Optional[str]
    total_input_rows: int
    valid_output_rows: int
    rejected_rows: int
    columns: List[str]
    duration_seconds: float
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le résultat en dictionnaire sérialisable."""
        return asdict(self)


def clean_column_name(col: str) -> str:
    """Normalise un nom de colonne en snake_case strict sans accents ni symboles.

    Exemples :
        "Périmètre" -> "perimetre"
        "Consommation (MW)" -> "consommation_mw"
        "Prévision J-1 (MW)" -> "prevision_j1_mw"
        "Taux de CO2 (g/kWh)" -> "taux_co2_g_kwh"
        "Hydraulique - Fil de l'eau + éclusée (MW)" -> "hydraulique_fil_eau_eclusee_mw"
        "codeEICResourceObject" -> "code_eic"
        "puisMaxInstallee" -> "puis_max_installee_kw"

    Args:
        col: Nom de colonne brut.

    Returns:
        str: Nom normalisé en snake_case.
    """
    # 1. Suppression du BOM UTF-8 éventuel et espaces
    clean_raw = col.strip().lstrip("\ufeff")

    # 2. Remplacements de noms explicites prioritaires (RTE / Enedis)
    replacements = {
        "Date et Heure": "date_heure",
        "Date - Heure": "date_heure",
        "Date et heure": "date_heure",
        "Taux de CO2 (g/kWh)": "taux_co2_g_kwh",
        "Ech. physiques (MW)": "ech_physiques_mw",
        "codeEICResourceObject": "code_eic",
        "codeIRISCommuneImplantation": "code_iris_commune_implantation",
        "codeINSEECommuneImplantation": "code_insee_commune_implantation",
        "codeINSEECommune": "code_insee_commune",
        "codeIRIS": "code_iris",
        "codeEPCI": "code_epci",
        "codeDepartement": "code_departement",
        "codeRegion": "code_region",
        "codeS3RENR": "code_s3renr",
        "codeGestionnaire": "code_gestionnaire",
        "nomInstallation": "nom_installation",
        "dateRaccordement": "date_raccordement",
        "dateDeraccordement": "date_deraccordement",
        "dateMiseEnService": "date_mise_en_service",
        "dateDebutVersion": "date_debut_version",
        "posteSource": "poste_source",
        "tensionRaccordement": "tension_raccordement",
        "modeRaccordement": "mode_raccordement",
        "codeFiliere": "code_filiere",
        "codeTechnologie": "code_technologie",
        "puisMaxInstallee": "puis_max_installee_kw",
        "puisMaxRac": "puis_max_rac_kw",
        "puisMaxCharge": "puis_max_charge_kw",
        "puisMaxRacCharge": "puis_max_rac_charge_kw",
        "puisMaxInstalleeDisCharge": "puis_max_installee_discharge_kw",
        "nbGroupes": "nb_groupes",
        "nbInstallations": "nb_installations",
        "energieAnnuelleGlissanteInjectee": "energie_annuelle_glissante_injectee_kwh",
        "energieAnnuelleGlissanteProduite": "energie_annuelle_glissante_produite_kwh",
        "energieAnnuelleGlissanteSoutiree": "energie_annuelle_glissante_soutiree_kwh",
        "energieAnnuelleGlissanteStockee": "energie_annuelle_glissante_stockee_kwh",
        "energieStockable": "energie_stockable_kwh",
        "capaciteReservoir": "capacite_reservoir",
        "hauteurChute": "hauteur_chute_m",
        "debitMaximal": "debit_maximal_m3_s",
        "typeStockage": "type_stockage",
        "maxPuis": "max_puis_kw",
        "dateMiseEnservice (format date)": "date_mise_en_service_iso",
    }
    if clean_raw in replacements:
        return replacements[clean_raw]

    # 3. Remplacements d'unités spécifiques avant nettoyage
    name = clean_raw
    name = re.sub(r"\(MW\)", "_mw", name, flags=re.IGNORECASE)
    name = re.sub(r"\(kW\)", "_kw", name, flags=re.IGNORECASE)
    name = re.sub(r"\(kWh\)", "_kwh", name, flags=re.IGNORECASE)
    name = re.sub(r"\(g/kWh\)", "_g_kwh", name, flags=re.IGNORECASE)
    name = re.sub(r"\(%\)", "_pct", name, flags=re.IGNORECASE)
    name = re.sub(r"\bJ-1\b", "j1", name, flags=re.IGNORECASE)

    # 4. Décomposition Unicode pour retirer les accents
    nfkd_form = unicodedata.normalize("NFKD", name)
    name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # 5. Conversion CamelCase vers snake_case générique
    name = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)

    # 6. Remplacement des caractères non alphanumériques par des underscores
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)

    # 7. Nettoyage des underscores consécutifs ou en bordure
    name = re.sub(r"_+", "_", name).strip("_").lower()

    return name
