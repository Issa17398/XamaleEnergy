-- ==============================================================================
-- Observatoire des données énergétiques de la France
-- Script 02 : Dimensions du modèle en étoile (Couche Gold)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Dimension Temps (Granularité demi-heure)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_temps (
    date_heure TIMESTAMPTZ PRIMARY KEY,
    date DATE NOT NULL,
    heure VARCHAR(5) NOT NULL,
    annee INT NOT NULL,
    mois INT NOT NULL,
    mois_nom VARCHAR(15) NOT NULL,
    jour INT NOT NULL,
    jour_semaine INT NOT NULL,
    jour_semaine_nom VARCHAR(15) NOT NULL,
    trimestre INT NOT NULL,
    semaine INT NOT NULL,
    saison VARCHAR(10) NOT NULL,
    est_weekend BOOLEAN NOT NULL,
    est_jour_ferie BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_dim_temps_date ON gold.dim_temps (date);
CREATE INDEX IF NOT EXISTS idx_dim_temps_annee_mois ON gold.dim_temps (annee, mois);

-- ------------------------------------------------------------------------------
-- 2. Dimension Géographie Administrative
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_geographie (
    code_insee_commune VARCHAR(10) PRIMARY KEY,
    commune VARCHAR(150),
    code_departement VARCHAR(5),
    departement VARCHAR(100),
    code_region VARCHAR(5),
    region VARCHAR(100),
    code_epci VARCHAR(20),
    epci VARCHAR(150)
);

CREATE INDEX IF NOT EXISTS idx_dim_geo_dept ON gold.dim_geographie (code_departement);
CREATE INDEX IF NOT EXISTS idx_dim_geo_region ON gold.dim_geographie (code_region);

-- ------------------------------------------------------------------------------
-- 3. Dimension Filière Énergétique
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_filiere (
    code_filiere VARCHAR(50) PRIMARY KEY,
    libelle_filiere VARCHAR(100) NOT NULL,
    categorie_energie VARCHAR(50) NOT NULL,
    est_renouvelable BOOLEAN NOT NULL,
    est_pilotable BOOLEAN NOT NULL
);

-- Données de référence standardisées
INSERT INTO gold.dim_filiere (code_filiere, libelle_filiere, categorie_energie, est_renouvelable, est_pilotable)
VALUES
    ('solaire', 'Énergie Solaire Photovoltaïque', 'Renouvelable', TRUE, FALSE),
    ('eolien', 'Énergie Éolienne (Terrestre et En Mer)', 'Renouvelable', TRUE, FALSE),
    ('hydraulique', 'Énergie Hydraulique', 'Renouvelable', TRUE, TRUE),
    ('bioenergies', 'Bioénergies (Biomasse, Biogaz, Déchets)', 'Renouvelable', TRUE, TRUE),
    ('nucleaire', 'Énergie Nucléaire', 'Décarbonée / Fissile', FALSE, TRUE),
    ('gaz', 'Gaz Naturel Thermique', 'Fossile', FALSE, TRUE),
    ('charbon', 'Charbon Thermique', 'Fossile', FALSE, TRUE),
    ('fioul', 'Fioul Thermique', 'Fossile', FALSE, TRUE),
    ('pompage', 'Pompage Hydraulique (STEP)', 'Stockage', FALSE, TRUE),
    ('stockage', 'Stockage par Batterie', 'Stockage', FALSE, TRUE),
    ('autre', 'Autre technologie non spécifiée', 'Autre', FALSE, FALSE)
ON CONFLICT (code_filiere) DO NOTHING;
