"""Routeur des métriques clés et snapshot instantané du mix électrique."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text

from src.energy_observatory.api.dependencies import get_db_connection
from src.energy_observatory.api.schemas import (
    CrossBorderFlows,
    EnergyMixBreakdown,
    LatestMetricsResponse,
)

router = APIRouter(prefix="/metrics", tags=["Métriques Réseau"])


@router.get(
    "/latest",
    response_model=LatestMetricsResponse,
    summary="Snapshot instantané du réseau électrique français",
    description="Retourne le dernier point de mesure (30 min) disponible avec production par filière, parts décarbonée/renouvelable, CO2 et échanges.",
)
def get_latest_metrics(conn: Connection = Depends(get_db_connection)) -> LatestMetricsResponse:
    """Récupère l'enregistrement le plus récent de la table fact_electricite_national_30min."""
    query = text("""
        SELECT
            date_heure,
            consommation_mw,
            prevision_j1_mw,
            prevision_j_mw,
            nucleaire_mw,
            eolien_mw,
            solaire_mw,
            hydraulique_mw,
            pompage_mw,
            gaz_mw,
            charbon_mw,
            fioul_mw,
            bioenergies_mw,
            ech_physiques_mw,
            taux_co2_g_kwh,
            ech_comm_angleterre_mw,
            ech_comm_espagne_mw,
            ech_comm_italie_mw,
            ech_comm_suisse_mw,
            ech_comm_allemagne_belgique_mw,
            production_totale_mw,
            production_renouvelable_mw
        FROM gold.fact_electricite_national_30min
        ORDER BY date_heure DESC
        LIMIT 1;
    """)

    row = conn.execute(query).mappings().fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune donnée d'électricité trouvée dans la couche Gold.",
        )

    prod_totale = float(row["production_totale_mw"] or 0.0)
    prod_renouv = float(row["production_renouvelable_mw"] or 0.0)
    nucleaire = float(row["nucleaire_mw"] or 0.0)
    fossile = float((row["gaz_mw"] or 0.0) + (row["charbon_mw"] or 0.0) + (row["fioul_mw"] or 0.0))

    part_renouvelable = round((prod_renouv / prod_totale * 100.0), 2) if prod_totale > 0 else 0.0
    part_decarbonee = round(((nucleaire + prod_renouv) / prod_totale * 100.0), 2) if prod_totale > 0 else 0.0
    part_fossile = round((fossile / prod_totale * 100.0), 2) if prod_totale > 0 else 0.0

    ech_phys = float(row["ech_physiques_mw"] or 0.0)
    if ech_phys < -100.0:
        statut_solde = "Exportateur net"
    elif ech_phys > 100.0:
        statut_solde = "Importateur net"
    else:
        statut_solde = "Équilibré"

    filieres = EnergyMixBreakdown(
        nucleaire_mw=nucleaire,
        eolien_mw=float(row["eolien_mw"] or 0.0),
        solaire_mw=float(row["solaire_mw"] or 0.0),
        hydraulique_mw=float(row["hydraulique_mw"] or 0.0),
        pompage_mw=float(row["pompage_mw"] or 0.0),
        gaz_mw=float(row["gaz_mw"] or 0.0),
        charbon_mw=float(row["charbon_mw"] or 0.0),
        fioul_mw=float(row["fioul_mw"] or 0.0),
        bioenergies_mw=float(row["bioenergies_mw"] or 0.0),
    )

    echanges = CrossBorderFlows(
        ech_physiques_mw=ech_phys,
        angleterre_mw=float(row["ech_comm_angleterre_mw"]) if row["ech_comm_angleterre_mw"] is not None else None,
        espagne_mw=float(row["ech_comm_espagne_mw"]) if row["ech_comm_espagne_mw"] is not None else None,
        italie_mw=float(row["ech_comm_italie_mw"]) if row["ech_comm_italie_mw"] is not None else None,
        suisse_mw=float(row["ech_comm_suisse_mw"]) if row["ech_comm_suisse_mw"] is not None else None,
        allemagne_belgique_mw=float(row["ech_comm_allemagne_belgique_mw"]) if row["ech_comm_allemagne_belgique_mw"] is not None else None,
        statut_solde=statut_solde,
    )

    return LatestMetricsResponse(
        date_heure=row["date_heure"].isoformat() if hasattr(row["date_heure"], "isoformat") else str(row["date_heure"]),
        consommation_mw=float(row["consommation_mw"] or 0.0),
        prevision_j_mw=float(row["prevision_j_mw"]) if row["prevision_j_mw"] is not None else None,
        prevision_j1_mw=float(row["prevision_j1_mw"]) if row["prevision_j1_mw"] is not None else None,
        production_totale_mw=prod_totale,
        production_renouvelable_mw=prod_renouv,
        part_renouvelable_pct=part_renouvelable,
        part_decarbonee_pct=part_decarbonee,
        part_fossile_pct=part_fossile,
        taux_co2_g_kwh=float(row["taux_co2_g_kwh"] or 0.0),
        filieres=filieres,
        echanges=echanges,
    )
