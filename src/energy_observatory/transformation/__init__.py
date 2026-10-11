"""Package de transformation et nettoyage des données (Couche Silver)."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cleaning import TransformationResult, clean_column_name
    from .rte_transform import transform_rte_national_bronze_to_silver
    from .enedis_transform import transform_enedis_registre_bronze_to_silver
    from .world_bank_transform import transform_world_bank_bronze_to_silver
else:
    def transform_rte_national_bronze_to_silver(*args, **kwargs):
        from .rte_transform import transform_rte_national_bronze_to_silver as _impl
        return _impl(*args, **kwargs)

    def transform_enedis_registre_bronze_to_silver(*args, **kwargs):
        from .enedis_transform import transform_enedis_registre_bronze_to_silver as _impl
        return _impl(*args, **kwargs)

    def transform_world_bank_bronze_to_silver(*args, **kwargs):
        from .world_bank_transform import transform_world_bank_bronze_to_silver as _impl
        return _impl(*args, **kwargs)

    def clean_column_name(*args, **kwargs):
        from .cleaning import clean_column_name as _impl
        return _impl(*args, **kwargs)


__all__ = [
    "TransformationResult",
    "clean_column_name",
    "transform_rte_national_bronze_to_silver",
    "transform_enedis_registre_bronze_to_silver",
    "transform_world_bank_bronze_to_silver",
]
