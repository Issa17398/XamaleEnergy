"""Modèles Pydantic pour la validation et la sérialisation des réponses API."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# Health Check
# ==============================================================================

class HealthResponse(BaseModel):
    """Modèle de réponse du statut de santé du service et de PostgreSQL."""
    status: str = Field(..., description="Statut global ('healthy' ou 'degraded')")
    database_connected: bool = Field(..., description="Connectivité PostgreSQL active")
    database_host: str = Field(..., description="Hôte de la base de données")
    database_port: int = Field(..., description="Port PostgreSQL")
    database_name: str = Field(..., description="Nom de la base active")
    tables_counts: Dict[str, int] = Field(..., description="Comptage des lignes par table")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Horodatage UTC du diagnostic",
    )


# ==============================================================================
# Métriques en temps réel / Dernier intervalle
# ==============================================================================

class EnergyMixBreakdown(BaseModel):
    """Détail de la puissance produite ou consommée par filière (en MW)."""
    nucleaire_mw: float = Field(..., description="Puissance nucléaire (MW)")
    eolien_mw: float = Field(..., description="Puissance éolienne terrestre et maritime (MW)")
    solaire_mw: float = Field(..., description="Puissance solaire photovoltaïque (MW)")
    hydraulique_mw: float = Field(..., description="Puissance hydraulique (MW)")
    pompage_mw: float = Field(..., description="Pompage hydraulique STEP (soutirage) (MW)")
    gaz_mw: float = Field(..., description="Puissance thermique gaz (MW)")
    charbon_mw: float = Field(..., description="Puissance thermique charbon (MW)")
    fioul_mw: float = Field(..., description="Puissance thermique fioul (MW)")
    bioenergies_mw: float = Field(..., description="Puissance bioénergies (MW)")


class CrossBorderFlows(BaseModel):
    """Échanges commerciaux et physiques aux frontières françaises (en MW)."""
    ech_physiques_mw: float = Field(..., description="Solde physique global (négatif = export, positif = import) (MW)")
    angleterre_mw: Optional[float] = Field(None, description="Échange commercial Angleterre (MW)")
    espagne_mw: Optional[float] = Field(None, description="Échange commercial Espagne (MW)")
    italie_mw: Optional[float] = Field(None, description="Échange commercial Italie (MW)")
    suisse_mw: Optional[float] = Field(None, description="Échange commercial Suisse (MW)")
    allemagne_belgique_mw: Optional[float] = Field(None, description="Échange commercial Allemagne-Belgique (MW)")
    statut_solde: str = Field(..., description="'Exportateur net' | 'Importateur net' | 'Équilibré'")


class LatestMetricsResponse(BaseModel):
    """Snapshot instantané du réseau électrique français pour le dernier pas de 30 min disponible."""
    date_heure: str = Field(..., description="Horodatage ISO 8601 du point de mesure")
    consommation_mw: float = Field(..., description="Consommation nationale observée (MW)")
    prevision_j_mw: Optional[float] = Field(None, description="Prévision de consommation J (MW)")
    prevision_j1_mw: Optional[float] = Field(None, description="Prévision de consommation J-1 (MW)")
    production_totale_mw: float = Field(..., description="Production électrique totale brute (MW)")
    production_renouvelable_mw: float = Field(..., description="Production renouvelable cumulée (MW)")
    part_renouvelable_pct: float = Field(..., description="Part renouvelable dans la production (%)")
    part_decarbonee_pct: float = Field(..., description="Part décarbonée (Nucléaire + Renouvelable) (%)")
    part_fossile_pct: float = Field(..., description="Part fossile (Gaz + Charbon + Fioul) (%)")
    taux_co2_g_kwh: float = Field(..., description="Intensité carbone de l'électricité produite (gCO2/kWh)")
    filieres: EnergyMixBreakdown = Field(..., description="Décomposition par filière")
    echanges: CrossBorderFlows = Field(..., description="Échanges transfrontaliers")


# ==============================================================================
# Séries Temporelles Énergie (Mix 30 min)
# ==============================================================================

class MixHistoryPoint(BaseModel):
    """Point d'observation sur le mix électrique à granularité 30 minutes."""
    date_heure: str = Field(..., description="Horodatage ISO")
    consommation_mw: float
    production_totale_mw: float
    production_renouvelable_mw: float
    part_renouvelable_pct: float
    part_decarbonee_pct: float
    nucleaire_mw: float
    eolien_mw: float
    solaire_mw: float
    hydraulique_mw: float
    gaz_mw: float
    charbon_mw: float
    fioul_mw: float
    bioenergies_mw: float
    pompage_mw: float
    ech_physiques_mw: float
    taux_co2_g_kwh: float


class MixHistoryResponse(BaseModel):
    """Réponse paginée pour l'historique du mix électrique."""
    total_records: int = Field(..., description="Nombre d'enregistrements retournés")
    start_date: Optional[str] = Field(None, description="Date de début demandée")
    end_date: Optional[str] = Field(None, description="Date de fin demandée")
    points: List[MixHistoryPoint] = Field(..., description="Points chronologiques")


# ==============================================================================
# Vue Agréguée Mensuelle
# ==============================================================================

class MonthlyMixPoint(BaseModel):
    """Agrégation mensuelle du mix électrique (depuis 2012)."""
    annee: int
    mois: int
    mois_nom: str
    nb_intervalles_30min: int
    conso_moyenne_mw: float
    pointe_consommation_mw: float
    prod_totale_moyenne_mw: float
    nucleaire_moyen_mw: float
    eolien_moyen_mw: float
    solaire_moyen_mw: float
    hydraulique_moyen_mw: float
    renouvelable_moyen_mw: float
    part_renouvelable_pct: float
    part_decarbonee_pct: float
    intensite_co2_moyenne_g_kwh: float


class MonthlyMixResponse(BaseModel):
    """Historique mensuel consolidé du mix électrique français."""
    total_records: int
    points: List[MonthlyMixPoint]


# ==============================================================================
# Capacités Installées (Enedis Registre 2025)
# ==============================================================================

class RegionalCapacityPoint(BaseModel):
    """Capacité installée par région administrative et filière de production."""
    region: str
    code_region: str
    code_filiere: str
    libelle_filiere: str
    categorie_energie: str
    nb_installations: int
    puissance_totale_mw: float


class RegionalCapacitiesResponse(BaseModel):
    """Réponse des capacités régionales installées."""
    total_records: int
    items: List[RegionalCapacityPoint]


class CategoryCapacitySummary(BaseModel):
    """Synthèse des puissances raccordées par grande catégorie énergétique."""
    categorie_energie: str
    nb_installations: int
    puissance_totale_mw: float
    part_pct: float


class CapacitiesSummaryResponse(BaseModel):
    """Synthèse nationale globale des capacités de production et stockage."""
    total_installations: int
    total_puissance_mw: float
    categories: List[CategoryCapacitySummary]


# ==============================================================================
# Indicateur International (Banque Mondiale)
# ==============================================================================

class InternationalAccessPoint(BaseModel):
    """Indicateur d'accès à l'électricité annuel."""
    annee: int
    pays_iso3: str
    pays_nom: str
    indicateur_id: str
    valeur_pct: Optional[float]
    is_missing: bool


class InternationalAccessResponse(BaseModel):
    """Série temporelle Banque Mondiale pour la France."""
    total_records: int
    points: List[InternationalAccessPoint]


# ==============================================================================
# Audit et Qualité des Données
# ==============================================================================

class QualityRuleDetail(BaseModel):
    """Résultat détaillé pour une règle d'intégrité ou physique."""
    code: str
    category: str
    description: str
    passed: bool
    severity: str
    measured_value: Any
    details: str


class QualityReportResponse(BaseModel):
    """Rapport d'audit de qualité des données automatisé."""
    generated_at: str
    global_score_pct: float
    total_rules: int
    passed_rules: int
    failed_rules: int
    status: str
    rules: List[QualityRuleDetail]
