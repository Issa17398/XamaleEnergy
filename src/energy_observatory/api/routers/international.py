"""Routeur pour les indicateurs internationaux (Banque Mondiale)."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from src.energy_observatory.api.dependencies import get_db_connection
from src.energy_observatory.api.schemas import (
    InternationalAccessPoint,
    InternationalAccessResponse,
)

router = APIRouter(prefix="/international", tags=["International & Comparaisons"])


@router.get(
    "/access",
    response_model=InternationalAccessResponse,
    summary="Taux d'accès à l'électricité en France (Banque Mondiale)",
    description="Série temporelle officielle du pourcentage de la population ayant accès à l'électricité (Indicateur EG.ELC.ACCS.ZS).",
)
def get_international_access(
    annee_min: Optional[int] = Query(None, description="Année de départ (ex: 1990)"),
    annee_max: Optional[int] = Query(None, description="Année de fin (ex: 2022)"),
    conn: Connection = Depends(get_db_connection),
) -> InternationalAccessResponse:
    """Interroge la table gold.fact_acces_electricite_annuel."""
    conditions = []
    params = {}

    if annee_min is not None:
        conditions.append("annee >= :annee_min")
        params["annee_min"] = annee_min
    if annee_max is not None:
        conditions.append("annee <= :annee_max")
        params["annee_max"] = annee_max

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query_sql = f"""
        SELECT
            annee,
            pays_iso3,
            pays_nom,
            indicateur_id,
            valeur_pct,
            is_missing
        FROM gold.fact_acces_electricite_annuel
        {where_clause}
        ORDER BY annee ASC;
    """

    rows = conn.execute(text(query_sql), params).mappings().fetchall()

    points = [
        InternationalAccessPoint(
            annee=int(r["annee"]),
            pays_iso3=str(r["pays_iso3"]),
            pays_nom=str(r["pays_nom"]),
            indicateur_id=str(r["indicateur_id"]),
            valeur_pct=float(r["valeur_pct"]) if r["valeur_pct"] is not None else None,
            is_missing=bool(r["is_missing"]),
        )
        for r in rows
    ]

    return InternationalAccessResponse(total_records=len(points), points=points)
