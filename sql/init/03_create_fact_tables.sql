-- ==============================================================================
-- Observatoire des données énergétiques de la France
-- Script 03 : Tables de Faits (Couche Gold)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Table de Faits : Électricité Nationale (Pas 30 minutes, 2012-2026)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_electricite_national_30min (
    date_heure TIMESTAMPTZ PRIMARY KEY REFERENCES gold.dim_temps(date_heure),
    consommation_mw DOUBLE PRECISION NOT NULL,
    prevision_j1_mw DOUBLE PRECISION,
    prevision_j_mw DOUBLE PRECISION,
    nucleaire_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    eolien_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    solaire_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    hydraulique_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    pompage_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    gaz_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    charbon_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    fioul_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    bioenergies_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ech_physiques_mw DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    taux_co2_g_kwh DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    ech_comm_angleterre_mw DOUBLE PRECISION,
    ech_comm_espagne_mw DOUBLE PRECISION,
    ech_comm_italie_mw DOUBLE PRECISION,
    ech_comm_suisse_mw DOUBLE PRECISION,
    ech_comm_allemagne_belgique_mw DOUBLE PRECISION,
    -- Colonnes calculées générées automatiquement
    production_totale_mw DOUBLE PRECISION GENERATED ALWAYS AS (
        nucleaire_mw + eolien_mw + solaire_mw + hydraulique_mw + gaz_mw + charbon_mw + fioul_mw + bioenergies_mw
    ) STORED,
    production_renouvelable_mw DOUBLE PRECISION GENERATED ALWAYS AS (
        eolien_mw + solaire_mw + hydraulique_mw + bioenergies_mw
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_fact_elec_date_heure_desc 
ON gold.fact_electricite_national_30min (date_heure DESC);

-- ------------------------------------------------------------------------------
-- 2. Table de Faits : Registre des Installations de Production & Stockage
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_registre_installations (
    id_installation BIGSERIAL PRIMARY KEY,
    nom_installation VARCHAR(255),
    code_eic VARCHAR(50),
    code_insee_commune VARCHAR(10) REFERENCES gold.dim_geographie(code_insee_commune),
    code_filiere VARCHAR(50) REFERENCES gold.dim_filiere(code_filiere),
    filiere VARCHAR(100),
    technologie VARCHAR(100),
    combustible VARCHAR(100),
    puis_max_installee_kw DOUBLE PRECISION NOT NULL,
    puis_max_raccordee_kw DOUBLE PRECISION,
    tension_raccordement VARCHAR(50),
    date_mise_en_service DATE,
    annee_mise_en_service INT,
    regime VARCHAR(50),
    gestionnaire_reseau VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_fact_inst_filiere ON gold.fact_registre_installations (code_filiere);
CREATE INDEX IF NOT EXISTS idx_fact_inst_commune ON gold.fact_registre_installations (code_insee_commune);
CREATE INDEX IF NOT EXISTS idx_fact_inst_annee ON gold.fact_registre_installations (annee_mise_en_service);
CREATE INDEX IF NOT EXISTS idx_fact_inst_puissance ON gold.fact_registre_installations (puis_max_installee_kw DESC);

-- ------------------------------------------------------------------------------
-- 3. Table de Faits : Indicateur International Banque Mondiale
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.fact_acces_electricite_annuel (
    annee INT PRIMARY KEY,
    pays_iso3 VARCHAR(3) NOT NULL,
    pays_nom VARCHAR(100) NOT NULL,
    indicateur_id VARCHAR(50) NOT NULL,
    valeur_pct DOUBLE PRECISION,
    is_missing BOOLEAN NOT NULL DEFAULT FALSE
);
