"""Package des routeurs FastAPI."""

from src.energy_observatory.api.routers.health import router as health_router
from src.energy_observatory.api.routers.metrics import router as metrics_router
from src.energy_observatory.api.routers.mix import router as mix_router
from src.energy_observatory.api.routers.capacities import router as capacities_router
from src.energy_observatory.api.routers.international import router as international_router
from src.energy_observatory.api.routers.quality import router as quality_router

__all__ = [
    "health_router",
    "metrics_router",
    "mix_router",
    "capacities_router",
    "international_router",
    "quality_router",
]
