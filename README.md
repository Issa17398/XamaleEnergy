# Observatoire des Données Énergétiques de la France

> **Projet de Data Engineering & Architecture Analytique**  
> Collecte, historisation, transformation et valorisation des données publiques de l'énergie en France.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Etalab%202.0%20%2F%20MIT-green.svg)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
[![Architecture](https://img.shields.io/badge/architecture-Medallion%20(Bronze%20%2F%20Silver%20%2F%20Gold)-orange.svg)](#architecture-data-engineering)
[![Status](https://img.shields.io/badge/phase-Phase%2011%20(Frontend%20React%20Validé)-success.svg)](#feuille-de-route-et-avancement)

---

## 1. Présentation et Objectifs du Projet

L'**Observatoire des données énergétiques de la France** est un système complet de Data Engineering conçu pour collecter, auditer, stocker, nettoyer, historiser et analyser les données publiques relatives au système électrique français :
- **Consommation & Production électrique** nationale et régionale en temps réel et consolidée.
- **Mix énergétique français** par filière (Nucléaire, Éolien, Solaire photovoltaïque, Hydraulique, Gaz, Charbon, Fioul, Bioénergies).
- **Échanges transfrontaliers** physiques et commerciaux avec les pays limitrophes (Royaume-Uni, Espagne, Italie, Suisse, Allemagne/Belgique).
- **Intensité carbone (g CO2/kWh)** de la production électrique.
- **Cartographie des capacités installées** : Registre national exhaustif des installations de production et de stockage (notamment photovoltaïque).
- **Contexte macro-énergétique international** : Taux d'accès à l'électricité (Banque Mondiale).

### Principes Directeurs
1. **Data Engineering First** : Le backend API et le tableau de bord web ne sont construits qu'après validation complète et reproductibilité des pipelines de données.
2. **Aucune donnée inventée** : Chaque colonne, chaque valeur et chaque métrique provient d'une source officielle vérifiée.
3. **Simplicité & Sobriété** : Architecture locale performante (`Python 3.13`, `pandas`, `SQLAlchemy`, `PostgreSQL`), sans empilement prématuré d'outils distribués (Kafka/Spark/Kubernetes non requis au démarrage).
4. **Reproductibilité & Traçabilité** : Sauvegarde immuable des flux bruts avec métadonnées d'ingestion (date de collecte, checksum SHA-256, statut HTTP, volume).

---

## 2. Architecture Data Engineering

Le projet s'appuie sur une **architecture en trois couches (modèle Medallion)** :

```
                  SOURCES OFFICIELLES VÉRIFIÉES
            (RTE éCO2mix | Enedis Registre | Banque Mondiale)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ COUCHE BRONZE (data/raw/)                                       │
│ • Données sources brutes immuables (CSV / JSON natifs)         │
│ • Métadonnées d'ingestion sidecar (metadata_*.json)             │
│ • Checksum SHA-256, horodatage UTC, statut HTTP, volumétrie     │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Ingestion & Validation
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ COUCHE SILVER (data/processed/ & data/rejected/)                │
│ • Normalisation des schémas et typages stricts                 │
│ • Harmonisation temporelle (fuseaux UTC et pas 30 min)          │
│ • Gestion explicite des anomalies (rejets isolés et documentés) │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Modélisation Relationnelle
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ COUCHE GOLD (Base PostgreSQL - Vues Analytiques & Marts)        │
│ • Tables de faits temporelles (fact_hourly_production)          │
│ • Tables de dimensions géographiques et filières                │
│ • Indicateurs agrégés précalculés pour l'API et le Dashboard   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Sources de Données Officielles (Audit Phase 1)

L'audit détaillé avec les schémas complets est consigné dans [docs/sources.md](docs/sources.md).

| Source | Rôle Métier | Format & Volume | Granularité | Statut |
| :--- | :--- | :--- | :--- | :--- |
| **Source A — RTE éCO2mix National** | Production par filière, consommation, échanges, CO2 | CSV (~83,8 Mo) / 514 272 lignes | 30 min (réalisé) / 15 min (prévision) | **Vérifiée** |
| **Source A — RTE éCO2mix Régional** | Consommation et mix par région administrative | CSV / Quota ODRÉ 50k req/mois | 30 min | **Vérifiée** |
| **Source B — Enedis / Registre National** | Installations de production & stockage au 31/12/2025 | CSV (~40,5 Mo) / 125 930 installations | Annuel (stock capacitaire kW) | **Vérifiée** |
| **Source C — Banque Mondiale** | Taux d'accès à l'électricité (`EG.ELC.ACCS.ZS`) | JSON API (~14 Ko) / 66 points | Annuel (1960–2025) | **Vérifiée** |

> **Règle métier capitale** : Le Registre National (Source B) recense des **capacités installées en kW (stock)**, tandis que RTE (Source A) mesure des **puissances appelées en MW et énergies produites en MWh (flux)**. Elles ne doivent jamais être sommées directement.

---

## 4. Organisation du Répertoire

```
French_energy/
├── .env.example                # Modèle documenté des variables d'environnement
├── .env                        # Configuration locale (non versionnée)
├── .gitignore                  # Exclusion des données brutes, venv, secrets, caches
├── pyproject.toml              # Dépendances Python modernes (PEP 621) et config pytest
├── README.md                   # Documentation maîtresse du projet
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Classe Settings immuable avec résolution des chemins
│
├── data/                       # Stockage des données (arborescence conservée par .gitkeep)
│   ├── raw/                    # Couche Bronze (flux bruts)
│   │   ├── rte/
│   │   ├── enedis/
│   │   └── world_bank/
│   ├── processed/              # Couche Silver (données nettoyées)
│   └── rejected/               # Données rejetées lors des contrôles qualité
│
├── docs/
│   └── sources.md              # Audit exhaustif des 3 sources de données
│
├── logs/                       # Fichiers de logs tournants (energy_observatory.log)
│
├── src/
│   └── energy_observatory/
│       ├── __init__.py
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── rte.py              # Ingestion résiliente RTE éCO2mix (Couche Bronze)
│       │   ├── enedis.py           # Ingestion Registre National des installations (Couche Bronze)
│       │   └── world_bank.py       # Ingestion indicateurs Banque Mondiale (Couche Bronze)
│       └── utils/
│           ├── __init__.py
│           └── logging_config.py   # Configuration standardisée des logs (console + fichier)
│
└── tests/
    ├── __init__.py
    ├── test_environment.py        # Tests automatisés de l'environnement et des settings
    ├── test_rte_ingestion.py      # Tests d'ingestion RTE (streaming, SHA-256, résilience HTTP)
    ├── test_enedis_ingestion.py   # Tests d'ingestion Enedis (millésime 2025, idempotence)
    └── test_world_bank_ingestion.py # Tests d'ingestion Banque Mondiale (JSON, nulls, validation)
```

---

## 5. Prérequis et Installation Pas à Pas

### Prérequis
- **Python 3.11, 3.12 ou 3.13** installé sur votre machine.
- **Git** installé.
- **Docker** (recommandé pour la base PostgreSQL ultérieure).

### 1. Cloner ou ouvrir le projet
```powershell
cd "c:\Users\7MAKSACOD PC\Desktop\French_energy"
```

### 2. Créer et activer l'environnement virtuel
Sous Windows (PowerShell) :
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(Sous Linux / macOS : `source .venv/bin/activate`)*

### 3. Installer les dépendances
```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Configurer les variables d'environnement
Un fichier `.env.example` est fourni. Pour initialiser votre fichier local :
```powershell
Copy-Item .env.example .env
```

---

## 6. Vérification, Ingestion et Exécution des Tests

### A. Lancer la suite complète de tests unitaires (`pytest`)
```powershell
.\.venv\Scripts\pytest -v
```

Exemple de résultat attendu (31 tests passés avec succès) :
```text
tests/test_enedis_ingestion.py::test_ingest_enedis_success_with_mock PASSED [  3%]
tests/test_enedis_ingestion.py::test_ingest_enedis_http_error PASSED     [  6%]
tests/test_enedis_ingestion.py::test_ingest_enedis_idempotence PASSED    [  9%]
tests/test_environment.py::test_settings_paths PASSED                    [ 12%]
tests/test_environment.py::test_settings_ensure_directories PASSED       [ 16%]
tests/test_environment.py::test_settings_urls_configured PASSED          [ 19%]
tests/test_environment.py::test_logger_setup PASSED                      [ 22%]
tests/test_quality.py::test_models_serialization PASSED                  [ 25%]
tests/test_quality.py::test_markdown_report_generation PASSED            [ 29%]
tests/test_quality.py::test_export_quality_report PASSED                 [ 32%]
tests/test_quality.py::test_validator_live_db_checks PASSED              [ 35%]
tests/test_rte_ingestion.py::test_inspect_csv_file PASSED                [ 38%]
tests/test_rte_ingestion.py::test_ingest_rte_success_with_mock PASSED    [ 41%]
tests/test_rte_ingestion.py::test_ingest_rte_http_error PASSED           [ 45%]
tests/test_rte_ingestion.py::test_ingest_rte_idempotence PASSED          [ 48%]
tests/test_storage.py::test_settings_database_url PASSED                 [ 51%]
tests/test_storage.py::test_sql_init_scripts_presence_and_structure PASSED [ 54%]
tests/test_storage.py::test_map_filiere_code PASSED                      [ 58%]
tests/test_storage.py::test_dim_temps_feature_engineering PASSED         [ 61%]
tests/test_storage.py::test_load_fact_worldbank PASSED                   [ 64%]
tests/test_storage.py::test_load_silver_to_gold_orchestration PASSED     [ 67%]
tests/test_transformation.py::TestCleaningUtils::test_clean_column_name_accents_and_units PASSED [ 70%]
tests/test_transformation.py::TestCleaningUtils::test_clean_column_name_enedis_mappings PASSED [ 74%]
tests/test_transformation.py::TestRteTransformation::test_rte_silver_transform_filters_forecasts_and_exports_parquet PASSED [ 77%]
tests/test_transformation.py::TestEnedisTransformation::test_enedis_silver_transform_preserves_strings_and_handles_rejections PASSED [ 80%]
tests/test_transformation.py::TestWorldBankTransformation::test_world_bank_silver_transform_preserves_missing_and_validates PASSED [ 83%]
tests/test_world_bank_ingestion.py::test_inspect_world_bank_payload PASSED [ 87%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_success_with_mock PASSED [ 90%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_http_error PASSED [ 93%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_invalid_structure PASSED [ 96%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_idempotence PASSED [100%]
====================== 31 passed in 2.79s ======================
```

### B. Exécuter l'ingestion du flux RTE éCO2mix National (Bronze)
```powershell
.\.venv\Scripts\python -m src.energy_observatory.ingestion.rte
```

### C. Exécuter l'ingestion du Registre National Enedis (Bronze)
```powershell
.\.venv\Scripts\python -m src.energy_observatory.ingestion.enedis
```

### D. Exécuter l'ingestion de la Banque Mondiale (Bronze)
```powershell
.\.venv\Scripts\python -m src.energy_observatory.ingestion.world_bank
```

> **Options disponibles :**
> - Exécution normale : interroge l'API pour la France (`FRA`) et l'indicateur d'accès (`EG.ELC.ACCS.ZS`).
> - Forcer le re-téléchargement : `.\.venv\Scripts\python -m src.energy_observatory.ingestion.world_bank --force`
> - Cibler un autre pays ou indicateur :
>   ```powershell
>   .\.venv\Scripts\python -m src.energy_observatory.ingestion.world_bank --country FRA --indicator EG.ELC.ACCS.ZS
>   ```

Exemple de rapport d'ingestion généré :
```text
--- Rapport d'ingestion Banque Mondiale ---
Statut : SUCCESS
Indicateur : EG.ELC.ACCS.ZS (Access to electricity (% of population))
Pays : FRA
Fichier brut : .../data/raw/world_bank/worldbank_FRA_EG_ELC_ACCS_ZS_20261011.json
Taille : 14314 octets
SHA-256 : 6835f2b00dc123d19327bd125221d844125c1ede8d94c242f62c5a474a88c345
Total observations : 66
Observations valides : 35
Observations nulles (manquantes) : 31
Période couverte : 1960 - 2025
Durée : ~2 s
```

```

### E. Exécuter le pipeline de transformation Silver (Toutes les sources)
Pour transformer l'ensemble des données brutes Bronze en jeux de données nettoyés, typés et optimisés au format Parquet :
```powershell
.\.venv\Scripts\python -m src.energy_observatory.transformation.run_all
```

Vous pouvez également lancer la transformation d'une source spécifique de manière autonome :
```powershell
# Transformation RTE éCO2mix (Pas 30 min, typage, gestion des auxiliaires)
.\.venv\Scripts\python -m src.energy_observatory.transformation.rte_transform

# Transformation Enedis Registre National (Codes géographiques préservés, dates ISO)
.\.venv\Scripts\python -m src.energy_observatory.transformation.enedis_transform

# Transformation Banque Mondiale (Aplatissement, indicateurs is_missing, tri chronologique)
.\.venv\Scripts\python -m src.energy_observatory.transformation.world_bank_transform
```

Exemple de bilan généré en sortie de pipeline :
```text
======================================================================
BILAN COMPLET DU PIPELINE DE TRANSFORMATION SILVER
======================================================================

[Source] RTE_ECO2MIX_NATIONAL
  - Statut           : SUCCESS
  - Lignes entrantes : 514,272
  - Lignes valides   : 257,105
  - Lignes rejetées  : 30 (doublons d'horodatage UTC)
  - Fichier Parquet  : data/processed/silver_rte_national_30min.parquet (11.2 Mo, compression x7.3)
  - Fichier rejets   : data/rejected/rte_rejected_20261011.csv
  - Colonnes (24)    : perimetre, nature, date, heure, date_heure, consommation_mw, nucleaire_mw, eolien_mw, solaire_mw... (13 sous-filières absentes en 2012 purgées pour garantir 100% de complétude)
  - Durée            : ~4.9 s

[Source] ENEDIS_REGISTRE_INSTALLATIONS
  - Statut           : SUCCESS
  - Lignes entrantes : 125,930
  - Lignes valides   : 125,885
  - Lignes rejetées  : 45 (33 sans capacité, 12 sans géographie)
  - Fichier Parquet  : data/processed/silver_enedis_registre_2025.parquet (6.1 Mo, compression x6.3)
  - Fichier rejets   : data/rejected/enedis_rejected_20261011.csv
  - Colonnes (33)    : nom_installation, code_eic, code_iris, code_insee_commune, commune... (18 colonnes mortes/redondantes éliminées)
  - Durée            : ~2.4 s

[Source] WORLDBANK_ACCESS_ELECTRICITY
  - Statut           : SUCCESS
  - Lignes entrantes : 66
  - Lignes valides   : 66
  - Lignes rejetées  : 0
  - Fichier Parquet  : data/processed/silver_worldbank_access_electricity.parquet (6 Ko)
  - Colonnes (9)     : indicator_id, indicator_name, country_iso2, year, valeur_pct, is_missing...
  - Durée            : ~0.01 s
======================================================================
```

### F. Inspecter les données Silver (Statistiques, distributions et extraits)
Un outil d'exploration analytique dédié permet d'inspecter en direct les volumétries, distributions et échantillons :
```powershell
# Inspection complète des 3 sources + quarantaine des rejets
.\.venv\Scripts\python -m src.energy_observatory.analysis.inspect_silver

# Ou cibler une source en particulier
.\.venv\Scripts\python -m src.energy_observatory.analysis.inspect_silver --source rte
.\.venv\Scripts\python -m src.energy_observatory.analysis.inspect_silver --source enedis
.\.venv\Scripts\python -m src.energy_observatory.analysis.inspect_silver --source worldbank
.\.venv\Scripts\python -m src.energy_observatory.analysis.inspect_silver --source rejects
```

### G. Modélisation et Stockage PostgreSQL (Couche Gold)
Pour démarrer la base de données PostgreSQL isolée dans Docker et charger le modèle en étoile :

1. **Démarrer le conteneur PostgreSQL 16 (avec initialisation automatique DDL)** :
```powershell
docker compose up -d
```

2. **Exécuter le pipeline de chargement Silver vers Gold** :
```powershell
.\.venv\Scripts\python -m src.energy_observatory.storage.load_gold
```

Exemple de rapport attendu :
```text
============================================================
BILAN DU CHARGEMENT GOLD POSTGRESQL
============================================================
Statut                  : SUCCESS
gold.dim_temps          : 257,105 lignes
gold.dim_geographie     : 14,834 communes
gold.dim_filiere        : 11 technologies de référence
gold.fact_electricite   : 257,105 lignes
gold.fact_registre      : 125,885 installations
gold.fact_worldbank     : 66 observations
Vues analytiques créées : gold.v_mix_energetique_mensuel, gold.v_capacites_par_region
============================================================
### H. Contrôle Qualité & Audit Automatique des Données (Couche Gold)
Pour exécuter la suite de 10 contrôles d'intégrité, de physique du réseau et de continuité, et générer les rapports d'audit :
```powershell
.\.venv\Scripts\python -m src.energy_observatory.quality.validator
```

Exemple de rapport généré :
```text
======================================================================
BILAN DU CONTRÔLE QUALITÉ DES DONNÉES (COUCHE GOLD)
======================================================================
Statut Global        : PASS
Score de Qualité     : 100.00%
Règles Validées      : 10/10
Avertissements       : 0
Échecs Critiques     : 0
Durée d'exécution    : 0.59 s
----------------------------------------------------------------------
[OK]   [VOL-01] Volumétrie et couverture temporelle RTE
[OK]   [TIME-01] Continuité temporelle (pas 30 minutes)
[OK]   [REF-01] Intégrité référentielle Fact RTE -> Dim Temps
[OK]   [REF-02] Intégrité référentielle Fact Registre -> Dim Filière
[OK]   [REF-03] Intégrité référentielle Fact Registre -> Dim Géographie
[OK]   [PHYS-01] Équilibre physique réseau (Consommation vs Injection nette)
[OK]   [BOUND-01] Bornes physiques réalistes RTE (Conso, Nucléaire, CO2)
[OK]   [BOUND-02] Plausibilité des capacités installées Enedis
[OK]   [NULL-01] Complétude des métriques de production et consommation
[OK]   [WB-01] Cohérence indicateur Banque Mondiale (Accès électricité FRA)
======================================================================
Rapports d'audit générés :
  - data/reports/data_quality_report_20261011.md
  - data/reports/data_quality_report_20261011.json
```

### I. Exécuter le Pipeline Complet End-to-End (Toutes les Couches)
Un orchestrateur central permet d'exécuter l'intégralité du cycle de vie de la donnée (Bronze -> Silver -> Gold -> Quality) en une seule commande avec rapport consolidé :

```powershell
# Exécuter l'ensemble du pipeline (Bronze -> Silver -> Gold -> Qualité)
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage all

# Ou exécuter une étape ciblée
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage bronze
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage silver
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage gold
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage quality

# Option pour forcer le re-téléchargement des sources Bronze
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage all --force
```

Exemple de rapport consolidé :
```text
======================================================================
BILAN D'EXÉCUTION DU PIPELINE DE DONNÉES (END-TO-END)
======================================================================
Statut Global        : SUCCESS
Durée Totale         : 71.85 s
Score Qualité Final  : 100.00%
----------------------------------------------------------------------
Étape                      | Statut    | Durée    | Détails
----------------------------------------------------------------------
1. BRONZE_INGESTION        | [OK]      |  0.60 s | RTE: 514,272 lig., Enedis: 125,930 lig.
2. SILVER_TRANSFORMATION   | [OK]      | 18.85 s | Parquet générés (RTE 257k, Enedis 125k, WB 66)
3. GOLD_LOADING            | [OK]      | 51.75 s | PostgreSQL: 257,105 faits, 26,829 communes
4. QUALITY_VALIDATION      | [OK]      |  0.65 s | Score: 100.0% (10/10 règles)
======================================================================
```

---

## 7. Règles Métier Appliquées en Couche Silver

| Source | Règle Métier & Justification | Traitement appliqué |
|---|---|---|
| **RTE** | **Granularité mixte (15 min vs 30 min)** : à :15 et :45, seules les prévisions sont publiées. La réalisation effective n'existe qu'à :00 et :30. | Isolation des 257 105 mesures réelles (`consommation_mw.notna()`) pour les tables de faits historiques. |
| **RTE** | **Soutirage d'auxiliaires à l'arrêt** : la nuit, les onduleurs solaires consomment ~-1 MW sur le réseau; les centrales thermiques à l'arrêt consomment ~-15 MW d'auxiliaires. | Clamping de la production brute à `0.0 MW`. Les aberrations physiques sévères (< -500 MW) sont rejetées. |
| **Enedis** | **Codes géographiques administratifs** : les codes de communes ou départements (`01`, `2A`, `974`) perdent leur zéro initial s'ils sont convertis en entiers. | Typage strict forcé en `string` dès la lecture CSV. |
| **Enedis** | **Unités de puissance** : les puissances installées sont en **kW** (inventaire de capacité), contrairement à RTE qui est en **MW** (flux d'énergie). | Suffixe explicite `puis_max_installee_kw` et typage float64. |
| **Banque Mondiale** | **Historique avec trous de collecte** : l'accès à l'électricité n'est mesuré que depuis 1990 (35 années valides sur 66). | Conservation des 66 points avec un indicateur booléen `is_missing` pour intégrité statistique. |
| **Toutes** | **Optimisation du stockage analytique** : les fichiers CSV bruts (~120 Mo) sont lourds à requêter. | Conversion au format Apache Parquet (Snappy), réduisant l'empreinte disque globale à ~19.4 Mo (gain x6.2). |

---

## 8. Backend API REST (FastAPI)

Le backend expose l'ensemble des données de la couche Gold (tables de faits, dimensions et vues analytiques) via une API RESTful haute performance construite avec **FastAPI**, validée par **Pydantic v2** et servie par **Uvicorn**.

### Démarrage du Serveur API

```powershell
# Lancement du serveur en mode développement avec rechargement automatique
.\.venv\Scripts\uvicorn src.energy_observatory.api.main:app --reload --port 8000
```

- **Documentation Interactive (Swagger UI)** : [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentation ReDoc** : [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Spécification OpenAPI 3** : [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Catalogue des Endpoints Disponibles

| Méthode | Route | Rôle Métier & Paramètres | Modèle de Réponse |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Métadonnées de l'API, version et annuaire des endpoints | JSON informatif |
| `GET` | `/health` / `/api/v1/health` | Diagnostic de santé, connectivité PostgreSQL et comptage des 6 tables | `HealthResponse` |
| `GET` | `/api/v1/metrics/latest` | Snapshot instantané du réseau : consommation, production, % décarboné, flux transfrontaliers, CO2 | `LatestMetricsResponse` |
| `GET` | `/api/v1/mix/history` | Séries temporelles 30 min (filtres `start_date`, `end_date`, `limit` max 2000) | `MixHistoryResponse` |
| `GET` | `/api/v1/mix/monthly` | Historique mensuel consolidé 2012-2026 (filtres `annee`, `limit`) | `MonthlyMixResponse` |
| `GET` | `/api/v1/capacities/regional` | Capacités installées par région et filière (filtres `code_region`, `code_filiere`) | `RegionalCapacitiesResponse` |
| `GET` | `/api/v1/capacities/summary` | Synthèse nationale des puissances installées par catégorie énergétique | `CapacitiesSummaryResponse` |
| `GET` | `/api/v1/international/access` | Évolution du taux d'accès à l'électricité en France (filtres `annee_min`, `annee_max`) | `InternationalAccessResponse` |
| `GET` | `/api/v1/quality/report` | Rapport des 10 règles de validation de données (paramètre `refresh=true` pour audit en direct) | `QualityReportResponse` |

---

## 9. Frontend React Dashboard (Thème & Identité Xamale)

Le tableau de bord web interactif est développé en **React + Vite**, stylisé en **Vanilla CSS / CSS Modules haute fidélité** avec la palette chromatique dérivée du **logo Xamale** (Midnight Deep Navy `#050C18`, Radiant Gold `#F5B82E`, Glassmorphism `#0D1B31`, typographies Google Fonts *Outfit* et *Inter*).

### Démarrage de l'Application Frontend

```powershell
# Accéder au dossier frontend et lancer le serveur Vite
cd frontend
npm run dev
```

L'application est immédiatement accessible à l'adresse : **[http://localhost:5173/](http://localhost:5173/)** (avec proxy API automatique configuré vers `http://localhost:8000`).

### Modules & Fonctionnalités Intégrés

1. **⚡ Temps Réel & Mix National** :
   - Cartouches KPI temps réel : Consommation nationale (MW), Production totale (MW), Part d'électricité décarbonée (%), Intensité carbone (gCO2/kWh), Solde net aux frontières.
   - Graphique interactif Recharts (30 minutes) empilé par filière technologique (Nucléaire, Hydraulique, Éolien, Solaire, Bioénergies, Thermique) avec courbe de consommation.
   - Sélecteur temporel dynamique : 24 heures, 48 heures ou 7 jours.
   - Baromètre d'interconnexion européen avec les 5 pays frontaliers (Royaume-Uni, Espagne, Italie, Suisse, Allemagne/Belgique).
2. **📅 Historique Mensuel (2012–2026)** :
   - Suivi pluriannuel issu de la vue Gold `gold.v_mix_energetique_mensuel`.
   - Comparaison de la consommation moyenne et des pointes hivernales.
   - Évolution de la part décarbonée et de la baisse tendancielle de l'intensité CO2.
   - Filtrage dynamique par millésime.
3. **🗺️ Registre & Capacités Installées (Enedis 2025)** :
   - Synthèse nationale du parc de production et stockage (125 885 installations raccordées, ~147 000 MW cumulés).
   - Palmarès horizontal des 10 premières régions productrices.
   - Moteur de recherche et filtre instantané par région administrative ou technologie.
4. **🛡️ Audit & Fiabilité des Données (10/10 PASS)** :
   - Moniteur interactif affichant le score de qualité parfait de 100.0%.
   - Présentation détaillée des 10 règles de validation physique, mathématique et d'intégrité relationnelle.
   - Bouton d'exécution en direct pour recalculer l'audit à la demande.
5. **🌍 Indicateur International Banque Mondiale** :
   - Série historique officielle du taux d'électrification (100.0% depuis 1990).
   - Documentation de la conservation scientifique des 66 points avec indicateur `is_missing`.

---

## 10. Feuille de Route et Avancement

- [x] **Phase 0 — Diagnostic de l'environnement & Cadrage technique** (Python 3.13, Docker, Git, architecture Medallion retenue).
- [x] **Phase 1 — Audit complet des 3 sources de données** (Vérification des APIs RTE, Enedis, Banque Mondiale; rédaction de [docs/sources.md](docs/sources.md)).
- [x] **Phase 2 — Mise en place de l'environnement & Outillage** (`pyproject.toml`, `.gitignore`, `.env`, `settings.py`, `logging_config.py`, tests automatisés).
- [x] **Phase 3 — Première Ingestion : RTE éCO2mix National (Bronze)** (Module streaming résilient, 514 272 lignes, 37 colonnes, métadonnées JSON, tests validés).
- [x] **Phase 4 — Ingestion : Enedis Registre National (Bronze)** (Millésime 31/12/2025, 125 930 installations, 51 colonnes, métadonnées JSON, tests validés).
- [x] **Phase 5 — Ingestion : Banque Mondiale (Bronze)** (API REST, 66 points 1960-2025, préservation des nulls, métadonnées JSON, tests validés).
- [x] **Phase 6 — Pipeline de Transformation Silver** (Nettoyage snake_case, typage strict, gestion des auxiliaires, quarantaine des rejets, export Parquet compressé x6.2, 21 tests unitaires validés).
- [x] **Phase 7 — Modélisation et Stockage PostgreSQL (Couche Gold)** (Docker Compose PostgreSQL 16, modèle dimensionnel en étoile, DDL schémas/tables/vues, loader optimisé COPY, 27 tests unitaires validés).
- [x] **Phase 8 — Contrôle Qualité, Validation Automatique & Fiabilité** (10 règles SQL automatisées, équilibre physique du réseau validé, rapports d'audit JSON/Markdown, 31 tests unitaires validés).
- [x] **Phase 9 — Pipeline Complet & Automatisation** (Orchestrateur unifié end-to-end, CLI tout-en-un avec `--stage`, bilan d'exécution synthétique, 36 tests unitaires validés).
- [x] **Phase 10 — Backend FastAPI** (API RESTful modulaire, 9 routeurs/endpoints, CORS configuré, validation Pydantic v2, 51 tests unitaires avec 94% de couverture).
- [x] **Phase 11 — Frontend React Dashboard** (Tableau de bord interactif React + Vite, identité de marque Xamale avec logo et favicon, 5 onglets analytiques, graphiques Recharts, build de production validé).
- [ ] **Phase 12 — Industrialisation Docker & Déploiement** *(Prochaine étape)*.



