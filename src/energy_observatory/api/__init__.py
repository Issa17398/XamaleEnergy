"""Package API REST (FastAPI) de l'Observatoire Énergétique de la France."""

from src.energy_observatory.api.main import app, create_app

__all__ = ["app", "create_app"]
