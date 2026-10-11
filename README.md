# Observatoire des Données Énergétiques de la France

> **Projet de Data Engineering & Architecture Analytique**  
> Collecte, historisation, transformation et valorisation des données publiques de l'énergie en France.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Etalab%202.0%20%2F%20MIT-green.svg)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
[![Architecture](https://img.shields.io/badge/architecture-Medallion%20(Bronze%20%2F%20Silver%20%2F%20Gold)-orange.svg)](#architecture-data-engineering)
[![Status](https://img.shields.io/badge/phase-Phase%205%20(Ingestion%20Banque%20Mondiale%20Validée)-success.svg)](#feuille-de-route-et-avancement)

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

Exemple de résultat attendu (16 tests passés avec succès) :
```text
tests/test_enedis_ingestion.py::test_ingest_enedis_success_with_mock PASSED [  6%]
tests/test_enedis_ingestion.py::test_ingest_enedis_http_error PASSED     [ 12%]
tests/test_enedis_ingestion.py::test_ingest_enedis_idempotence PASSED    [ 18%]
tests/test_environment.py::test_settings_paths PASSED                    [ 25%]
tests/test_environment.py::test_settings_ensure_directories PASSED       [ 31%]
tests/test_environment.py::test_settings_urls_configured PASSED          [ 37%]
tests/test_environment.py::test_logger_setup PASSED                      [ 43%]
tests/test_rte_ingestion.py::test_inspect_csv_file PASSED                [ 50%]
tests/test_rte_ingestion.py::test_ingest_rte_success_with_mock PASSED    [ 56%]
tests/test_rte_ingestion.py::test_ingest_rte_http_error PASSED           [ 62%]
tests/test_rte_ingestion.py::test_ingest_rte_idempotence PASSED          [ 68%]
tests/test_world_bank_ingestion.py::test_inspect_world_bank_payload PASSED [ 75%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_success_with_mock PASSED [ 81%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_http_error PASSED [ 87%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_invalid_structure PASSED [ 93%]
tests/test_world_bank_ingestion.py::test_ingest_world_bank_idempotence PASSED [100%]
====================== 16 passed in 1.89s ======================
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
  - Lignes rejetées  : 30
  - Fichier Parquet  : data/processed/silver_rte_national_30min.parquet (13.3 Mo, compression x6.2)
  - Fichier rejets   : data/rejected/rte_rejected_20261011.csv
  - Colonnes (37)    : perimetre, nature, date, heure, date_heure, consommation_mw...
  - Durée            : ~4.8 s

[Source] ENEDIS_REGISTRE_INSTALLATIONS
  - Statut           : SUCCESS
  - Lignes entrantes : 125,930
  - Lignes valides   : 125,930
  - Lignes rejetées  : 0
  - Fichier Parquet  : data/processed/silver_enedis_registre_2025.parquet (6.1 Mo, compression x6.3)
  - Colonnes (51)    : nom_installation, code_eic, code_iris, code_insee_commune...
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

## 8. Feuille de Route et Avancement

- [x] **Phase 0 — Diagnostic de l'environnement & Cadrage technique** (Python 3.13, Docker, Git, architecture Medallion retenue).
- [x] **Phase 1 — Audit complet des 3 sources de données** (Vérification des APIs RTE, Enedis, Banque Mondiale; rédaction de [docs/sources.md](docs/sources.md)).
- [x] **Phase 2 — Mise en place de l'environnement & Outillage** (`pyproject.toml`, `.gitignore`, `.env`, `settings.py`, `logging_config.py`, tests automatisés).
- [x] **Phase 3 — Première Ingestion : RTE éCO2mix National (Bronze)** (Module streaming résilient, 514 272 lignes, 37 colonnes, métadonnées JSON, tests validés).
- [x] **Phase 4 — Ingestion : Enedis Registre National (Bronze)** (Millésime 31/12/2025, 125 930 installations, 51 colonnes, métadonnées JSON, tests validés).
- [x] **Phase 5 — Ingestion : Banque Mondiale (Bronze)** (API REST, 66 points 1960-2025, préservation des nulls, métadonnées JSON, tests validés).
- [x] **Phase 6 — Pipeline de Transformation Silver** (Nettoyage snake_case, typage strict, gestion des auxiliaires, quarantaine des rejets, export Parquet compressé x6.2, 21 tests unitaires validés).
- [ ] **Phase 7 — Modélisation et Stockage PostgreSQL** *(Prochaine étape)* (Conteneur Docker, schémas Bronze/Silver/Gold, modélisation dimensionnelle étoiles, faits et dimensions).
- [ ] **Phase 8 — Contrôle Qualité & Fiabilité** (Tests de validation, règles métier, rapports qualité).
- [ ] **Phase 9 — Pipeline Complet & Automatisation**.
- [ ] **Phase 10 — Backend FastAPI**.
- [ ] **Phase 11 — Frontend React Dashboard**.
- [ ] **Phase 12 — Industrialisation Docker & Déploiement**.

