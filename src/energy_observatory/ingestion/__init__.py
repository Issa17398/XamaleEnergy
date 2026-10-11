"""Package d'ingestion des sources brutes (Couche Bronze)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rte import IngestionResult, ingest_rte_national_bronze
else:
    def ingest_rte_national_bronze(*args, **kwargs):
        from .rte import ingest_rte_national_bronze as _impl
        return _impl(*args, **kwargs)

__all__ = ["ingest_rte_national_bronze"]
