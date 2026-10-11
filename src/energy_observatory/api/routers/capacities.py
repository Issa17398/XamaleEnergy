"""Routeur pour les capacités de production et stockage installées (Registre Enedis 2025)."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from src.energy_observatory.api.dependencies import get_db_connection
from src.energy_observatory.api.schemas import (
    CapacitiesSummaryResponse,
    CategoryCapacitySummary,
    RegionalCapacitiesResponse,
    RegionalCapacityPoint,
)

router = APIRouter(prefix="/capacities", tags=["Capacités & Territoires"])


@router.get(
    "/regional",
    response_model=RegionalCapacitiesResponse,
    summary="Capacités installées par région et par filière",
    description="Retourne les capacités cumulées (MW) et le nombre d'installations par région depuis la vue analytique.",
)
def get_regional_capacities(
    code_region: Optional[str] = Query(None, description="Filtrer par code région (ex: '84', '11')"),
    code_filiere: Optional[str] = Query(None, description="Filtrer par code filière (ex: 'solaire', 'eolien')"),
    limit: int = Query(default=300, ge=1, le=1000, description="Nombre max de lignes"),
    conn: Connection = Depends(get_db_connection),
) -> RegionalCapacitiesResponse:
    """Interroge la vue gold.v_capacites_par_region."""
    conditions = []
    params = {"limit": limit}

    if code_region:
        conditions.append("code_region = :code_region")
        params["code_region"] = code_region
    if code_filiere:
        conditions.append("code_filiere = :code_filiere")
        params["code_filiere"] = code_filiere

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query_sql = f"""
        SELECT
            region,
            code_region,
            code_filiere,
            libelle_filiere,
            categorie_energie,
            nb_installations,
            puissance_totale_mw
        FROM gold.v_capacites_par_region
        {where_clause}
        ORDER BY puissance_totale_mw DESC
        LIMIT :limit;
    """

    rows = conn.execute(text(query_sql), params).mappings().fetchall()

    items = [
        RegionalCapacityPoint(
            region=str(r["region"]),
            code_region=str(r["code_region"]),
            code_filiere=str(r["code_filiere"]),
            libelle_filiere=str(r["libelle_filiere"]),
            categorie_energie=str(r["categorie_energie"]),
            nb_installations=int(r["nb_installations"]),
            puissance_totale_mw=float(r["puissance_totale_mw"] or 0.0),
        )
        for r in rows
    ]

    return RegionalCapacitiesResponse(total_records=len(items), items=items)


@router.get(
    "/summary",
    response_model=CapacitiesSummaryResponse,
    summary="Synthèse nationale des capacités de production",
    description="Agrège l'ensemble du registre national par catégorie d'énergie (Renouvelable, Décarbonée, Fossile, Stockage).",
)
def get_capacities_summary(conn: Connection = Depends(get_db_connection)) -> CapacitiesSummaryResponse:
    """Calcule la synthèse nationale des puissances installées."""
    query_sql = """
        SELECT
            COALESCE(df.categorie_energie, 'Autre') AS categorie_energie,
            COUNT(i.id_installation) AS nb_installations,
            ROUND(SUM(i.puis_max_installee_kw / 1000.0)::numeric, 2) AS puissance_totale_mw
        FROM gold.fact_registre_installations i
        JOIN gold.dim_filiere df ON i.code_filiere = df.code_filiere
        GROUP BY df.categorie_energie
        ORDER BY puissance_totale_mw DESC;
    """

    rows = conn.execute(text(query_sql)).mappings().fetchall()

    total_puissance = sum(float(r["puissance_totale_mw"] or 0.0) for r in rows)
    total_installs = sum(int(r["nb_installations"]) for r in rows)

    categories = [
        CategoryCapacitySummary(
            categorie_energie=str(r["categorie_energie"]),
            nb_installations=int(r["nb_installations"]),
            puissance_totale_mw=float(r["puissance_totale_mw"] or 0.0),
            part_pct=round((float(r["puissance_totale_mw"] or 0.0) / total_puissance * 100.0), 2)
            if total_puissance > 0
            else 0.0,
        )
        for r in rows
    ]

    return CapacitiesSummaryResponse(
        total_installations=total_installs,
        total_puissance_mw=round(total_puissance, 2),
        categories=categories,
    )
