-- ==============================================================================
-- Observatoire des données énergétiques de la France
-- Script 04 : Vues Analytiques & KPIs (Couche Gold)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Vue : Mix Énergétique Mensuel et Part Décarbonée
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.v_mix_energetique_mensuel AS
SELECT
    t.annee,
    t.mois,
    t.mois_nom,
    COUNT(*) AS nb_intervalles_30min,
    ROUND(AVG(f.consommation_mw)::numeric, 1) AS conso_moyenne_mw,
    ROUND(MAX(f.consommation_mw)::numeric, 1) AS pointe_consommation_mw,
    ROUND(AVG(f.production_totale_mw)::numeric, 1) AS prod_totale_moyenne_mw,
    ROUND(AVG(f.nucleaire_mw)::numeric, 1) AS nucleaire_moyen_mw,
    ROUND(AVG(f.eolien_mw)::numeric, 1) AS eolien_moyen_mw,
    ROUND(AVG(f.solaire_mw)::numeric, 1) AS solaire_moyen_mw,
    ROUND(AVG(f.hydraulique_mw)::numeric, 1) AS hydraulique_moyen_mw,
    ROUND(AVG(f.production_renouvelable_mw)::numeric, 1) AS renouvelable_moyen_mw,
    ROUND(
        (AVG(f.production_renouvelable_mw) / NULLIF(AVG(f.production_totale_mw), 0) * 100)::numeric,
        2
    ) AS part_renouvelable_pct,
    ROUND(
        ((AVG(f.nucleaire_mw) + AVG(f.production_renouvelable_mw)) / NULLIF(AVG(f.production_totale_mw), 0) * 100)::numeric,
        2
    ) AS part_decarbonee_pct,
    ROUND(AVG(f.taux_co2_g_kwh)::numeric, 1) AS intensite_co2_moyenne_g_kwh
FROM gold.fact_electricite_national_30min f
JOIN gold.dim_temps t ON f.date_heure = t.date_heure
GROUP BY t.annee, t.mois, t.mois_nom
ORDER BY t.annee DESC, t.mois DESC;

-- ------------------------------------------------------------------------------
-- 2. Vue : Synthèse des Capacités Installées par Région et Filière
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW gold.v_capacites_par_region AS
SELECT
    COALESCE(g.region, 'Non renseignée') AS region,
    COALESCE(g.code_region, 'NR') AS code_region,
    df.code_filiere,
    df.libelle_filiere,
    df.categorie_energie,
    COUNT(i.id_installation) AS nb_installations,
    ROUND(SUM(i.puis_max_installee_kw / 1000.0)::numeric, 2) AS puissance_totale_mw
FROM gold.fact_registre_installations i
JOIN gold.dim_filiere df ON i.code_filiere = df.code_filiere
LEFT JOIN gold.dim_geographie g ON i.code_insee_commune = g.code_insee_commune
GROUP BY g.region, g.code_region, df.code_filiere, df.libelle_filiere, df.categorie_energie
ORDER BY puissance_totale_mw DESC;
