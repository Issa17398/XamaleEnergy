"""Application principale FastAPI pour l'Observatoire Énergétique de la France."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from src.energy_observatory.api.routers import (
    capacities_router,
    health_router,
    international_router,
    metrics_router,
    mix_router,
    quality_router,
)
from src.energy_observatory.storage.db import check_connection
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger("energy_observatory.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestionnaire de cycle de vie de l'application FastAPI."""
    logger.info("=" * 60)
    logger.info("Démarrage de l'API de l'Observatoire Énergétique de la France")
    logger.info(f"Environnement : {settings.APP_ENV}")
    logger.info(f"Base de données cible : {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    # Vérification préliminaire de la connectivité PostgreSQL
    is_db_ready = check_connection()
    if is_db_ready:
        logger.info("[OK] Connexion au serveur PostgreSQL 16 opérationnelle.")
    else:
        logger.warning("[ATTENTION] Connexion PostgreSQL non disponible au démarrage.")

    yield

    logger.info("Arrêt de l'API de l'Observatoire Énergétique de la France.")
    logger.info("=" * 60)


def create_app() -> FastAPI:
    """Fabrique d'application FastAPI configurée avec middlewares et routeurs."""
    app_instance = FastAPI(
        title="Observatoire des Données Énergétiques de la France",
        description=(
            "API RESTful pour la consultation, l'analyse et la valorisation "
            "du mix électrique français en temps réel et historique (RTE éCO2mix 2012-2026), "
            "du registre national des capacités d'énergie et de stockage (Enedis 2025), "
            "et des indicateurs de la Banque Mondiale."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configuration CORS pour autoriser les interfaces web (React / Vite / Next.js)
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://localhost",
            "*",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Route de santé standard pour orchestrateurs (Docker / Kubernetes)
    app_instance.include_router(health_router)

    # Version 1 de l'API REST
    app_instance.include_router(health_router, prefix="/api/v1")
    app_instance.include_router(metrics_router, prefix="/api/v1")
    app_instance.include_router(mix_router, prefix="/api/v1")
    app_instance.include_router(capacities_router, prefix="/api/v1")
    app_instance.include_router(international_router, prefix="/api/v1")
    app_instance.include_router(quality_router, prefix="/api/v1")

    @app_instance.get("/", summary="Racine du service", tags=["Général"])
    def root() -> JSONResponse:
        """Point d'entrée de l'API avec métadonnées et navigation."""
        return JSONResponse(
            content={
                "service": "Observatoire des Données Énergétiques de la France",
                "version": "1.0.0",
                "status": "operational",
                "documentation": {
                    "swagger_ui": "/docs",
                    "redoc": "/redoc",
                    "openapi_spec": "/openapi.json",
                },
                "endpoints_v1": {
                    "health": "/api/v1/health",
                    "latest_metrics": "/api/v1/metrics/latest",
                    "mix_history_30min": "/api/v1/mix/history?limit=336",
                    "mix_monthly_summary": "/api/v1/mix/monthly",
                    "regional_capacities": "/api/v1/capacities/regional",
                    "national_capacities_summary": "/api/v1/capacities/summary",
                    "international_electricity_access": "/api/v1/international/access",
                    "data_quality_audit": "/api/v1/quality/report",
                },
            }
        )

    return app_instance


# Instance globale pour Uvicorn
app = create_app()
