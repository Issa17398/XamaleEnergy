"""Routeur de diagnostic et de vérification de santé (Health Check)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Connection, text

from config.settings import settings
from src.energy_observatory.api.dependencies import get_db_connection
from src.energy_observatory.api.schemas import HealthResponse

router = APIRouter(tags=["Santé & Diagnostic"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="État de santé du service et connectivité PostgreSQL",
    description="Vérifie la connexion à PostgreSQL et renvoie le comptage exact des tables du modèle en étoile.",
)
def get_health(conn: Connection = Depends(get_db_connection)) -> HealthResponse:
    """Vérifie l'accessibilité de la base de données et retourne les compteurs de lignes."""
    try:
        # 1. Ping rapide
        conn.execute(text("SELECT 1;"))

        # 2. Comptage des tables principales
        tables_to_check = [
            "gold.dim_temps",
            "gold.dim_geographie",
            "gold.dim_filiere",
            "gold.fact_electricite_national_30min",
            "gold.fact_registre_installations",
            "gold.fact_acces_electricite_annuel",
        ]
        counts = {}
        for tbl in tables_to_check:
            row = conn.execute(text(f"SELECT COUNT(*) FROM {tbl};")).scalar()
            counts[tbl] = int(row) if row is not None else 0

        return HealthResponse(
            status="healthy",
            database_connected=True,
            database_host=settings.POSTGRES_HOST,
            database_port=settings.POSTGRES_PORT,
            database_name=settings.POSTGRES_DB,
            tables_counts=counts,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "degraded",
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
