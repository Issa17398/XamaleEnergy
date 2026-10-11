"""Package d'ingestion des sources brutes (Couche Bronze)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rte import IngestionResult, ingest_rte_national_bronze
    from .enedis import EnedisIngestionResult, ingest_enedis_registre_bronze
    from .world_bank import WorldBankIngestionResult, ingest_world_bank_bronze
else:
    def ingest_rte_national_bronze(*args, **kwargs):
        from .rte import ingest_rte_national_bronze as _impl
        return _impl(*args, **kwargs)

    def ingest_enedis_registre_bronze(*args, **kwargs):
        from .enedis import ingest_enedis_registre_bronze as _impl
        return _impl(*args, **kwargs)

    def ingest_world_bank_bronze(*args, **kwargs):
        from .world_bank import ingest_world_bank_bronze as _impl
        return _impl(*args, **kwargs)

__all__ = [
    "ingest_rte_national_bronze",
    "ingest_enedis_registre_bronze",
    "ingest_world_bank_bronze",
]
