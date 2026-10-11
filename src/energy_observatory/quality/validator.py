"""Moteur de validation de la qualité des données (Data Quality Engine).

Exécute un ensemble exhaustif de règles métier, physiques et d'intégrité
sur les tables et dimensions de la couche Gold (PostgreSQL).
"""

import time
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.settings import settings
from src.energy_observatory.quality.models import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    QualityReport,
)
from src.energy_observatory.storage.db import get_engine
from src.energy_observatory.utils.logging_config import setup_logger

logger = setup_logger(__name__)


class DataQualityValidator:
    """Validateur de qualité des données pour l'Observatoire Énergétique."""

    def __init__(self, engine: Optional[Engine] = None):
        """Initialise le validateur avec le moteur de base de données.

        Args:
            engine: Instance Engine SQLAlchemy (défaut : get_engine()).
        """
        self.engine = engine or get_engine()

    def run_all_checks(self) -> QualityReport:
        """Exécute l'ensemble des règles de qualité et compile le rapport.

        Returns:
            QualityReport: Rapport global avec score et détails par règle.
        """
        start_time = time.time()
        logger.info("[Quality Engine] Démarrage de la suite de contrôles qualité Gold...")

        checks: List[CheckResult] = [
            self.check_fact_electricite_volume_and_range(),
            self.check_temporal_continuity(),
            self.check_referential_integrity_dim_temps(),
            self.check_referential_integrity_dim_filiere(),
            self.check_referential_integrity_dim_geographie(),
            self.check_grid_energy_balance(),
            self.check_rte_plausibility_boundaries(),
            self.check_enedis_plausibility_boundaries(),
            self.check_non_nullity_critical_metrics(),
            self.check_worldbank_indicator_bounds(),
        ]

        passed = sum(1 for c in checks if c.status == CheckStatus.PASS)
        warns = sum(1 for c in checks if c.status == CheckStatus.WARN)
        failed = sum(1 for c in checks if c.status == CheckStatus.FAIL)
        total = len(checks)

        # Calcul du score pondéré (PASS=1.0, WARN=0.5, FAIL=0.0)
        score = ((passed * 1.0 + warns * 0.5) / total) * 100.0 if total > 0 else 0.0

        if failed > 0:
            overall = CheckStatus.FAIL
        elif warns > 0:
            overall = CheckStatus.WARN
        else:
            overall = CheckStatus.PASS

        duration = round(time.time() - start_time, 2)
        logger.info(
            f"[Quality Engine] Validation terminée en {duration} s : "
            f"Score={score:.1f}% ({passed}/{total} passés, {warns} avertissements, {failed} échecs)."
        )

        return QualityReport(
            overall_status=overall,
            score_pct=score,
            total_checks=total,
            passed_checks=passed,
            warn_checks=warns,
            failed_checks=failed,
            duration_seconds=duration,
            checks=checks,
        )

    def check_fact_electricite_volume_and_range(self) -> CheckResult:
        """Vérifie la volumétrie minimale et la couverture temporelle de RTE."""
        query = text("""
            SELECT 
                COUNT(*) AS total_rows,
                MIN(date_heure) AS min_date,
                MAX(date_heure) AS max_date
            FROM gold.fact_electricite_national_30min;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        total_rows = row.total_rows if row else 0
        min_date = str(row.min_date) if row and row.min_date else "N/A"
        max_date = str(row.max_date) if row and row.max_date else "N/A"

        expected_min_rows = 250000
        status = CheckStatus.PASS if total_rows >= expected_min_rows else CheckStatus.FAIL

        return CheckResult(
            check_id="VOL-01",
            name="Volumétrie et couverture temporelle RTE",
            category=CheckCategory.VOLUME,
            status=status,
            metric_value=float(total_rows),
            threshold=float(expected_min_rows),
            message=f"{total_rows:,} lignes détectées entre {min_date} et {max_date}.",
            details={"min_date": min_date, "max_date": max_date, "total_rows": total_rows},
        )

    def check_temporal_continuity(self) -> CheckResult:
        """Vérifie l'absence de rupture dans la série temporelle au pas 30 minutes."""
        query = text("""
            WITH time_diffs AS (
                SELECT 
                    date_heure,
                    LAG(date_heure) OVER (ORDER BY date_heure) AS prev_date_heure
                FROM gold.fact_electricite_national_30min
            )
            SELECT 
                COUNT(*) AS total_intervals,
                COUNT(CASE WHEN date_heure - prev_date_heure > INTERVAL '30 minutes' THEN 1 END) AS gaps_count
            FROM time_diffs
            WHERE prev_date_heure IS NOT NULL;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        total = row.total_intervals if row else 1
        gaps = row.gaps_count if row else 0
        continuity_pct = ((total - gaps) / total) * 100.0 if total > 0 else 0.0

        threshold = 99.9
        status = CheckStatus.PASS if continuity_pct >= threshold else CheckStatus.WARN

        return CheckResult(
            check_id="TIME-01",
            name="Continuité temporelle (pas 30 minutes)",
            category=CheckCategory.COMPLETENESS,
            status=status,
            metric_value=continuity_pct,
            threshold=threshold,
            message=f"Taux de continuité : {continuity_pct:.4f}% ({gaps} écarts temporels > 30 min sur {total:,} intervalles).",
            details={"total_intervals": total, "gaps_count": gaps, "continuity_pct": continuity_pct},
        )

    def check_referential_integrity_dim_temps(self) -> CheckResult:
        """Garantit l'absence d'orphelins entre fact_electricite et dim_temps."""
        query = text("""
            SELECT COUNT(*) AS orphan_count
            FROM gold.fact_electricite_national_30min f
            LEFT JOIN gold.dim_temps t ON f.date_heure = t.date_heure
            WHERE t.date_heure IS NULL;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        orphans = row.orphan_count if row else 0
        status = CheckStatus.PASS if orphans == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="REF-01",
            name="Intégrité référentielle Fact RTE -> Dim Temps",
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            status=status,
            metric_value=float(orphans),
            threshold=0.0,
            message=f"Orphelins temporels détectés : {orphans}.",
            details={"orphan_count": orphans},
        )

    def check_referential_integrity_dim_filiere(self) -> CheckResult:
        """Garantit l'absence d'orphelins entre fact_registre et dim_filiere."""
        query = text("""
            SELECT COUNT(*) AS orphan_count
            FROM gold.fact_registre_installations i
            LEFT JOIN gold.dim_filiere f ON i.code_filiere = f.code_filiere
            WHERE f.code_filiere IS NULL;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        orphans = row.orphan_count if row else 0
        status = CheckStatus.PASS if orphans == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="REF-02",
            name="Intégrité référentielle Fact Registre -> Dim Filière",
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            status=status,
            metric_value=float(orphans),
            threshold=0.0,
            message=f"Installations sans filière valide : {orphans}.",
            details={"orphan_count": orphans},
        )

    def check_referential_integrity_dim_geographie(self) -> CheckResult:
        """Vérifie que les codes INSEE présents dans le registre sont référencés."""
        query = text("""
            SELECT COUNT(*) AS invalid_insee_count
            FROM gold.fact_registre_installations i
            WHERE i.code_insee_commune IS NOT NULL
              AND i.code_insee_commune NOT IN (SELECT code_insee_commune FROM gold.dim_geographie);
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        invalid_count = row.invalid_insee_count if row else 0
        status = CheckStatus.PASS if invalid_count == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="REF-03",
            name="Intégrité référentielle Fact Registre -> Dim Géographie",
            category=CheckCategory.REFERENTIAL_INTEGRITY,
            status=status,
            metric_value=float(invalid_count),
            threshold=0.0,
            message=f"Codes INSEE non référencés dans la dimension géographique : {invalid_count}.",
            details={"invalid_insee_count": invalid_count},
        )

    def check_grid_energy_balance(self) -> CheckResult:
        """Vérifie l'équation physique d'équilibre du réseau : Conso ≈ Prod + Échanges - Pompage."""
        query = text("""
            WITH balance_calc AS (
                SELECT 
                    consommation_mw,
                    production_totale_mw + ech_physiques_mw - pompage_mw AS bilan_injection_mw,
                    ABS(consommation_mw - (production_totale_mw + ech_physiques_mw - pompage_mw)) / NULLIF(consommation_mw, 0) AS ecart_relatif
                FROM gold.fact_electricite_national_30min
            )
            SELECT 
                COUNT(*) AS total_points,
                AVG(ecart_relatif) * 100 AS ecart_moyen_pct,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ecart_relatif) * 100 AS ecart_median_pct,
                COUNT(CASE WHEN ecart_relatif <= 0.10 THEN 1 END) AS points_conformes_10pct
            FROM balance_calc;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        total = row.total_points if row else 1
        conformes_10pct = row.points_conformes_10pct if row else 0
        compliance_pct = (conformes_10pct / total) * 100.0 if total > 0 else 0.0
        ecart_moyen = float(row.ecart_moyen_pct) if row and row.ecart_moyen_pct is not None else 0.0
        ecart_median = float(row.ecart_median_pct) if row and row.ecart_median_pct is not None else 0.0

        # En France, les pertes globales en ligne (RTE + Enedis) sont de 3% à 6% en moyenne
        # L'équilibre est validé si l'écart moyen <= 5% et l'écart médian <= 2%
        status = CheckStatus.PASS if (ecart_moyen <= 5.0 and ecart_median <= 2.0) else CheckStatus.WARN

        return CheckResult(
            check_id="PHYS-01",
            name="Équilibre physique réseau (Consommation vs Injection nette)",
            category=CheckCategory.PHYSICAL_CONSISTENCY,
            status=status,
            metric_value=ecart_median,
            threshold=2.0,
            message=(
                f"Écart médian réseau : {ecart_median:.2f}% (seuil <= 2.0%). "
                f"Écart moyen : {ecart_moyen:.2f}% (pertes transport/distribution attendues 3-5%). "
                f"Conformité tolérance 10% : {compliance_pct:.2f}%."
            ),
            details={
                "ecart_median_pct": ecart_median,
                "ecart_moyen_pct": ecart_moyen,
                "compliance_10pct": compliance_pct,
                "total_points": total,
            },
        )

    def check_rte_plausibility_boundaries(self) -> CheckResult:
        """Contrôle les bornes physiques réalistes sur les puissances et le CO2."""
        query = text("""
            SELECT 
                COUNT(CASE WHEN consommation_mw < 20000 OR consommation_mw > 120000 THEN 1 END) AS bad_conso,
                COUNT(CASE WHEN nucleaire_mw < 0 OR nucleaire_mw > 65000 THEN 1 END) AS bad_nuc,
                COUNT(CASE WHEN taux_co2_g_kwh < 0 OR taux_co2_g_kwh > 150 THEN 1 END) AS bad_co2,
                COUNT(*) AS total_rows
            FROM gold.fact_electricite_national_30min;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        bad_count = (row.bad_conso + row.bad_nuc + row.bad_co2) if row else 0
        total = row.total_rows if row else 1
        compliance_pct = ((total - bad_count) / total) * 100.0 if total > 0 else 0.0

        status = CheckStatus.PASS if bad_count == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="BOUND-01",
            name="Bornes physiques réalistes RTE (Conso, Nucléaire, CO2)",
            category=CheckCategory.BOUNDARY,
            status=status,
            metric_value=compliance_pct,
            threshold=100.0,
            message=f"{bad_count} valeurs hors limites physiques sur {total:,} mesures.",
            details={
                "bad_conso": row.bad_conso if row else 0,
                "bad_nuc": row.bad_nuc if row else 0,
                "bad_co2": row.bad_co2 if row else 0,
            },
        )

    def check_enedis_plausibility_boundaries(self) -> CheckResult:
        """Vérifie la plausibilité des capacités installées Enedis."""
        query = text("""
            SELECT 
                COUNT(CASE WHEN puis_max_installee_kw <= 0 OR puis_max_installee_kw > 2000000 THEN 1 END) AS bad_capacity,
                COUNT(*) AS total_installations
            FROM gold.fact_registre_installations;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        bad_count = row.bad_capacity if row else 0
        total = row.total_installations if row else 1
        compliance_pct = ((total - bad_count) / total) * 100.0 if total > 0 else 0.0

        status = CheckStatus.PASS if bad_count == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="BOUND-02",
            name="Plausibilité des capacités installées Enedis",
            category=CheckCategory.BOUNDARY,
            status=status,
            metric_value=compliance_pct,
            threshold=100.0,
            message=f"Capacités hors limites (> 0 kW et <= 2 GW) : {bad_count}/{total:,}.",
            details={"bad_capacity_count": bad_count, "total_installations": total},
        )

    def check_non_nullity_critical_metrics(self) -> CheckResult:
        """Contrôle l'absence totale de valeurs nulles sur les métriques critiques."""
        query = text("""
            SELECT 
                COUNT(CASE WHEN consommation_mw IS NULL THEN 1 END) AS null_conso,
                COUNT(CASE WHEN nucleaire_mw IS NULL THEN 1 END) AS null_nuc,
                COUNT(CASE WHEN eolien_mw IS NULL THEN 1 END) AS null_eol,
                COUNT(CASE WHEN solaire_mw IS NULL THEN 1 END) AS null_sol,
                COUNT(CASE WHEN taux_co2_g_kwh IS NULL THEN 1 END) AS null_co2,
                COUNT(*) AS total_rows
            FROM gold.fact_electricite_national_30min;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        null_count = (row.null_conso + row.null_nuc + row.null_eol + row.null_sol + row.null_co2) if row else 0
        status = CheckStatus.PASS if null_count == 0 else CheckStatus.FAIL

        return CheckResult(
            check_id="NULL-01",
            name="Complétude des métriques de production et consommation",
            category=CheckCategory.COMPLETENESS,
            status=status,
            metric_value=float(null_count),
            threshold=0.0,
            message=f"{null_count} valeurs nulles détectées sur les métriques clés de production et consommation.",
            details={"null_metrics_count": null_count},
        )

    def check_worldbank_indicator_bounds(self) -> CheckResult:
        """Vérifie l'indicateur d'accès à l'électricité de la Banque Mondiale."""
        query = text("""
            SELECT 
                COUNT(*) AS total_obs,
                COUNT(CASE WHEN is_missing = FALSE AND (valeur_pct < 90.0 OR valeur_pct > 100.0) THEN 1 END) AS out_of_bounds
            FROM gold.fact_acces_electricite_annuel;
        """)
        with self.engine.connect() as conn:
            row = conn.execute(query).fetchone()

        out_bounds = row.out_of_bounds if row else 0
        total = row.total_obs if row else 0
        status = CheckStatus.PASS if out_bounds == 0 and total == 66 else CheckStatus.WARN

        return CheckResult(
            check_id="WB-01",
            name="Cohérence indicateur Banque Mondiale (Accès électricité FRA)",
            category=CheckCategory.BOUNDARY,
            status=status,
            metric_value=float(total),
            threshold=66.0,
            message=f"{total} observations annuelles, {out_bounds} valeurs aberrantes hors 90-100%.",
            details={"total_observations": total, "out_of_bounds": out_bounds},
        )


if __name__ == "__main__":
    import argparse
    from src.energy_observatory.quality.reporter import export_quality_report

    parser = argparse.ArgumentParser(description="Moteur de validation de la qualité des données (Gold)")
    parser.add_argument("--no-export", action="store_true", help="Désactive l'export des fichiers JSON et Markdown")
    args = parser.parse_args()

    validator = DataQualityValidator()
    report = validator.run_all_checks()

    print("=" * 70)
    print("BILAN DU CONTRÔLE QUALITÉ DES DONNÉES (COUCHE GOLD)")
    print("=" * 70)
    print(f"Statut Global        : {report.overall_status.value}")
    print(f"Score de Qualité     : {report.score_pct:.2f}%")
    print(f"Règles Validées      : {report.passed_checks}/{report.total_checks}")
    print(f"Avertissements       : {report.warn_checks}")
    print(f"Échecs Critiques     : {report.failed_checks}")
    print(f"Durée d'exécution    : {report.duration_seconds} s")
    print("-" * 70)
    for c in report.checks:
        icon = "[OK]  " if c.status == CheckStatus.PASS else ("[WARN]" if c.status == CheckStatus.WARN else "[FAIL]")
        print(f"{icon} [{c.check_id}] {c.name}")
        print(f"       -> {c.message}")
    print("=" * 70)

    if not args.no_export:
        json_f, md_f = export_quality_report(report)
        print(f"Rapport Markdown généré : {md_f}")
        print(f"Rapport JSON structuré  : {json_f}")
        print("=" * 70)
