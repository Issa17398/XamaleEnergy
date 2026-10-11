# Observatoire des Données Énergétiques de la France

> **Projet de Data Engineering & Architecture Analytique**  
> Collecte, historisation, transformation et valorisation des données publiques de l'énergie en France.

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Etalab%202.0%20%2F%20MIT-green.svg)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/)
[![Architecture](https://img.shields.io/badge/architecture-Medallion%20(Bronze%20%2F%20Silver%20%2F%20Gold)-orange.svg)](#architecture-data-engineering)
[![Status](https://img.shields.io/badge/phase-Phase%203%20(Ingestion%20RTE%20Validée)-success.svg)](#feuille-de-route-et-avancement)

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
│       │   └── rte.py              # Ingestion résiliente RTE éCO2mix (Couche Bronze)
│       └── utils/
│           ├── __init__.py
│           └── logging_config.py   # Configuration standardisée des logs (console + fichier)
│
└── tests/
    ├── __init__.py
    ├── test_environment.py        # Tests automatisés de l'environnement et des settings
    └── test_rte_ingestion.py      # Tests d'ingestion RTE (streaming, SHA-256, résilience HTTP)
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

Exemple de résultat attendu (8 tests passés avec succès) :
```text
tests/test_environment.py::test_settings_paths PASSED                    [ 12%]
tests/test_environment.py::test_settings_ensure_directories PASSED       [ 25%]
tests/test_environment.py::test_settings_urls_configured PASSED          [ 37%]
tests/test_environment.py::test_logger_setup PASSED                      [ 50%]
tests/test_rte_ingestion.py::test_inspect_csv_file PASSED                [ 62%]
tests/test_rte_ingestion.py::test_ingest_rte_success_with_mock PASSED    [ 75%]
tests/test_rte_ingestion.py::test_ingest_rte_http_error PASSED           [ 87%]
tests/test_rte_ingestion.py::test_ingest_rte_idempotence PASSED          [100%]
============================== 8 passed in 0.46s ==============================
```

### B. Exécuter l'ingestion réelle du flux RTE éCO2mix National (Bronze)
```powershell
.\.venv\Scripts\python -m src.energy_observatory.ingestion.rte
```

> **Options disponibles :**
> - Exécution normale : vérifie si le fichier du jour existe déjà (`data/raw/rte/rte_national_YYYYMMDD.csv`). Si oui, évite le téléchargement redondant (idempotence).
> - Forcer le re-téléchargement :
>   ```powershell
>   .\.venv\Scripts\python -m src.energy_observatory.ingestion.rte --force
>   ```

Exemple de rapport d'ingestion généré :
```text
--- Rapport d'ingestion ---
Statut : SUCCESS
Source : RTE_ECO2MIX_NATIONAL
Fichier brut : .../data/raw/rte/rte_national_20261011.csv
Taille : 81.97 Mo
SHA-256 : b59dc719a0bf5dc6203dd715ff87be9c405026af58ab25c7bf54a61dc2ff3ca6
Nombre de lignes : 514,272
Nombre de colonnes : 37
Durée : ~50 s
```

---

## 7. Feuille de Route et Avancement

- [x] **Phase 0 — Diagnostic de l'environnement & Cadrage technique** (Python 3.13, Docker, Git, architecture Medallion retenue).
- [x] **Phase 1 — Audit complet des 3 sources de données** (Vérification des APIs RTE, Enedis, Banque Mondiale; rédaction de [docs/sources.md](docs/sources.md)).
- [x] **Phase 2 — Mise en place de l'environnement & Outillage** (`pyproject.toml`, `.gitignore`, `.env`, `settings.py`, `logging_config.py`, tests automatisés).
- [x] **Phase 3 — Première Ingestion : RTE éCO2mix National (Bronze)** (Module streaming résilient, 514 272 lignes, 37 colonnes, métadonnées JSON, tests validés).
- [ ] **Phase 4 — Ingestion : Enedis Registre National (Bronze)** *(Prochaine étape)*.
- [ ] **Phase 5 — Ingestion : Banque Mondiale (Bronze)**.
- [ ] **Phase 6 — Pipeline de Transformation Silver** (Nettoyage, harmonisation des pas 30 min, détection des anomalies).
- [ ] **Phase 7 — Modélisation et Stockage PostgreSQL** (Couche Gold, modélisation dimensionnelle).
- [ ] **Phase 8 — Contrôle Qualité & Fiabilité** (Tests de validation, règles métier, rapports qualité).
- [ ] **Phase 9 — Pipeline Complet & Automatisation**.
- [ ] **Phase 10 — Backend FastAPI**.
- [ ] **Phase 11 — Frontend React Dashboard**.
- [ ] **Phase 12 — Industrialisation Docker & Déploiement**.
