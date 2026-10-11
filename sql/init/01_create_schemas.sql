-- ==============================================================================
-- Observatoire des données énergétiques de la France
-- Script 01 : Création des schémas et extensions PostgreSQL
-- ==============================================================================

-- Activation des extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Création des schémas Medallion / Analytiques
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

COMMENT ON SCHEMA silver IS 'Couche Silver : données nettoyées, normalisées et typées';
COMMENT ON SCHEMA gold IS 'Couche Gold : modèle dimensionnel en étoile optimisé pour requêtes analytiques et BI';
