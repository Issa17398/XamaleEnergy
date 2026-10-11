"""Routeur pour les séries temporelles du mix électrique (demi-horaire et mensuel)."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from src.energy_observatory.api.dependencies import get_db_connection
from src.energy_observatory.api.schemas import (
    MixHistoryPoint,
    MixHistoryResponse,
    MonthlyMixPoint,
    MonthlyMixResponse,
)

router = APIRouter(prefix="/mix", tags=["Mix Électrique"])


@router.get(
    "/history",
    response_model=MixHistoryResponse,
    summary="Historique demi-horaire du mix électrique",
    description="Retourne les séries temporelles détaillées par pas de 30 minutes (consommation, production par filière, CO2).",
)
def get_mix_history(
    start_date: Optional[str] = Query(None, description="Date de début (ex: 2026-01-01 ou 2026-01-01T00:00:00)"),
    end_date: Optional[str] = Query(None, description="Date de fin (ex: 2026-01-07 ou 2026-01-07T23:30:00)"),
    limit: int = Query(default=336, ge=1, le=2000, description="Nombre de points (défaut: 336 = 7 jours)"),
    conn: Connection = Depends(get_db_connection),
) -> MixHistoryResponse:
    """Récupère l'historique demi-horaire du réseau électrique."""
    params = {"limit": limit}

    if start_date and end_date:
        query_sql = """
            SELECT
                date_heure,
                consommation_mw,
                production_totale_mw,
                production_renouvelable_mw,
                nucleaire_mw,
                eolien_mw,
                solaire_mw,
                hydraulique_mw,
                gaz_mw,
                charbon_mw,
                fioul_mw,
                bioenergies_mw,
                pompage_mw,
                ech_physiques_mw,
                taux_co2_g_kwh
            FROM gold.fact_electricite_national_30min
            WHERE date_heure >= :start_date AND date_heure <= :end_date
            ORDER BY date_heure ASC
            LIMIT :limit;
        """
        params["start_date"] = start_date
        params["end_date"] = end_date
    elif start_date:
        query_sql = """
            SELECT
                date_heure,
                consommation_mw,
                production_totale_mw,
                production_renouvelable_mw,
                nucleaire_mw,
                eolien_mw,
                solaire_mw,
                hydraulique_mw,
                gaz_mw,
                charbon_mw,
                fioul_mw,
                bioenergies_mw,
                pompage_mw,
                ech_physiques_mw,
                taux_co2_g_kwh
            FROM gold.fact_electricite_national_30min
            WHERE date_heure >= :start_date
            ORDER BY date_heure ASC
            LIMIT :limit;
        """
        params["start_date"] = start_date
    else:
        # Par défaut : les N derniers points disponibles, remis dans l'ordre chronologique croissant
        query_sql = """
            WITH recent_points AS (
                SELECT
                    date_heure,
                    consommation_mw,
                    production_totale_mw,
                    production_renouvelable_mw,
                    nucleaire_mw,
                    eolien_mw,
                    solaire_mw,
                    hydraulique_mw,
                    gaz_mw,
                    charbon_mw,
                    fioul_mw,
                    bioenergies_mw,
                    pompage_mw,
                    ech_physiques_mw,
                    taux_co2_g_kwh
                FROM gold.fact_electricite_national_30min
                ORDER BY date_heure DESC
                LIMIT :limit
            )
            SELECT * FROM recent_points
            ORDER BY date_heure ASC;
        """

    rows = conn.execute(text(query_sql), params).mappings().fetchall()

    points = []
    for r in rows:
        prod_tot = float(r["production_totale_mw"] or 0.0)
        prod_ren = float(r["production_renouvelable_mw"] or 0.0)
        nuc = float(r["nucleaire_mw"] or 0.0)

        part_ren = round((prod_ren / prod_tot * 100.0), 2) if prod_tot > 0 else 0.0
        part_dec = round(((nuc + prod_ren) / prod_tot * 100.0), 2) if prod_tot > 0 else 0.0

        points.append(
            MixHistoryPoint(
                date_heure=r["date_heure"].isoformat() if hasattr(r["date_heure"], "isoformat") else str(r["date_heure"]),
                consommation_mw=float(r["consommation_mw"] or 0.0),
                production_totale_mw=prod_tot,
                production_renouvelable_mw=prod_ren,
                part_renouvelable_pct=part_ren,
                part_decarbonee_pct=part_dec,
                nucleaire_mw=nuc,
                eolien_mw=float(r["eolien_mw"] or 0.0),
                solaire_mw=float(r["solaire_mw"] or 0.0),
                hydraulique_mw=float(r["hydraulique_mw"] or 0.0),
                gaz_mw=float(r["gaz_mw"] or 0.0),
                charbon_mw=float(r["charbon_mw"] or 0.0),
                fioul_mw=float(r["fioul_mw"] or 0.0),
                bioenergies_mw=float(r["bioenergies_mw"] or 0.0),
                pompage_mw=float(r["pompage_mw"] or 0.0),
                ech_physiques_mw=float(r["ech_physiques_mw"] or 0.0),
                taux_co2_g_kwh=float(r["taux_co2_g_kwh"] or 0.0),
            )
        )

    return MixHistoryResponse(
        total_records=len(points),
        start_date=start_date,
        end_date=end_date,
        points=points,
    )


@router.get(
    "/monthly",
    response_model=MonthlyMixResponse,
    summary="Synthèse mensuelle historique du mix électrique",
    description="Agrégation mensuelle calculée depuis la vue gold.v_mix_energetique_mensuel (2012-2026).",
)
def get_monthly_mix(
    annee: Optional[int] = Query(None, description="Filtrer par année (ex: 2025)"),
    limit: int = Query(default=120, ge=1, le=500, description="Nombre maximum de mois"),
    conn: Connection = Depends(get_db_connection),
) -> MonthlyMixResponse:
    """Interroge la vue gold.v_mix_energetique_mensuel."""
    if annee:
        query_sql = """
            SELECT *
            FROM gold.v_mix_energetique_mensuel
            WHERE annee = :annee
            ORDER BY annee DESC, mois DESC
            LIMIT :limit;
        """
        params = {"annee": annee, "limit": limit}
    else:
        query_sql = """
            SELECT *
            FROM gold.v_mix_energetique_mensuel
            ORDER BY annee DESC, mois DESC
            LIMIT :limit;
        """
        params = {"limit": limit}

    rows = conn.execute(text(query_sql), params).mappings().fetchall()

    points = [
        MonthlyMixPoint(
            annee=int(r["annee"]),
            mois=int(r["mois"]),
            mois_nom=str(r["mois_nom"]),
            nb_intervalles_30min=int(r["nb_intervalles_30min"]),
            conso_moyenne_mw=float(r["conso_moyenne_mw"] or 0.0),
            pointe_consommation_mw=float(r["pointe_consommation_mw"] or 0.0),
            prod_totale_moyenne_mw=float(r["prod_totale_moyenne_mw"] or 0.0),
            nucleaire_moyen_mw=float(r["nucleaire_moyen_mw"] or 0.0),
            eolien_moyen_mw=float(r["eolien_moyen_mw"] or 0.0),
            solaire_moyen_mw=float(r["solaire_moyen_mw"] or 0.0),
            hydraulique_moyen_mw=float(r["hydraulique_moyen_mw"] or 0.0),
            renouvelable_moyen_mw=float(r["renouvelable_moyen_mw"] or 0.0),
            part_renouvelable_pct=float(r["part_renouvelable_pct"] or 0.0),
            part_decarbonee_pct=float(r["part_decarbonee_pct"] or 0.0),
            intensite_co2_moyenne_g_kwh=float(r["intensite_co2_moyenne_g_kwh"] or 0.0),
        )
        for r in rows
    ]

    return MonthlyMixResponse(total_records=len(points), points=points)
