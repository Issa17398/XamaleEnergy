# XamaleEnergy — Observatoire des Données Énergétiques de la France

## 1. Présentation du projet
**XamaleEnergy** est une plateforme intégrée d'ingénierie de données (*Data Engineering*), d'audit qualité et d'analyse décisionnelle dédiée au système électrique français, architecturée selon le modèle **Medallion (Bronze / Silver / Gold)**.

L'application collecte, assainit, modélise, certifie et valorise les données ouvertes issues des opérateurs et institutions de référence du secteur énergétique : **RTE** (production, consommation, mix et flux transfrontaliers éCO2mix au pas 30 min), **Enedis** (registre national des 125 000+ installations de production et de stockage) et la **Banque Mondiale** (indicateur historique d'accès à l'électricité).

Face aux défis des données énergétiques brutes — discordances de granularité (prévisions 15 min vs réalisations 30 min), soutirage nocturne des auxiliaires générant des valeurs négatives (< 0 MW), confusion entre capacités installées en kW et flux en MW, troncature des codes géographiques —, **XamaleEnergy** structure la donnée en entrepôt relationnel **PostgreSQL 16**, garantit une fiabilité certifiée par un audit automatisé à **100% de conformité (10/10 règles)** et restitue l'ensemble via une API RESTful haute performance et un tableau de bord web interactif **React 19**.

---

## 2. Architecture Technique Épurée

Le projet est structuré selon les standards industriels du Data Engineering en **modules spécialisés et découplés** :

```text
French_energy
│
├── src/energy_observatory/        # ⚙️ Moteur Data Engineering & Backend API
│   ├── ingestion/                 # 📥 Couche Bronze : Ingestion streaming résiliente (RTE, Enedis, WB)
│   ├── transformation/            # 🔄 Couche Silver : Nettoyage, typage strict, clamping & Parquet
│   ├── storage/                   # 🏛️ Couche Gold : Modélisation Star Schema PostgreSQL & chargement
│   ├── quality/                   # 🛡️ Contrôle Qualité : Moteur d'audit SQL & physique (10/10 PASS)
│   ├── api/                       # 🚀 Backend FastAPI : Endpoints REST temps réel & historique
│   └── pipeline.py                # 🔁 Orchestrateur central CLI (Bronze -> Silver -> Gold -> Qualité)
│
├── frontend/                      # 💻 Interface utilisateur web décisionnelle
│   ├── src/                       # Composants React (Mix temps réel, historique, registre, audit)
│   └── package.json               # Dépendances frontend (React 19, Vite 8, Recharts 3.10)
│
├── sql/init/                      # 📄 Scripts d'initialisation DDL PostgreSQL (Montage Docker)
│   ├── 01_create_schemas.sql      # Schéma relationnel 'gold'
│   ├── 02_create_dimensions.sql   # Tables de dimensions (dim_temps, dim_geographie, dim_filiere)
│   ├── 03_create_fact_tables.sql  # Tables de faits (fact_electricite, fact_registre, fact_worldbank)
│   └── 04_create_views_analytics.sql # Vues matérialisées et agrégations mensuelles / régionales
│
├── data/                          # 💾 Données et persistance locale
│   ├── raw/                       # Couche Bronze : Flux bruts immuables & sidecars JSON (SHA-256)
│   ├── processed/                 # Couche Silver : Données nettoyées Apache Parquet Snappy (gain x7.3)
│   ├── rejected/                  # Quarantaine des rejets avec motifs d'exclusion documentés
│   └── reports/                   # Rapports de validation qualité générés (Markdown & JSON)
│
├── docker-compose.yml             # Conteneurisation de la base PostgreSQL 16 Alpine
├── pyproject.toml                 # Dépendances Python modernes et configuration du projet
└── .env.example                   # Modèle documenté des variables d'environnement
```

### Stack technologique
- **Architecture de Données** : Modèle Medallion (`Bronze` / `Silver` / `Gold`) avec modélisation dimensionnelle en étoile (*Star Schema*)
- **Traitement & Transformation** : `Python 3.13` (compatible `3.11+`), `pandas`, `pyarrow` (compression Snappy), `requests` (streaming 64 Ko)
- **Entrepôt de Données** : **PostgreSQL 16** via `Docker Compose`, `SQLAlchemy`, `psycopg2-binary`
- **Moteur d'Audit Qualité** : 10 règles automatisées d'intégrité et de physique réseau (validateur Pydantic v2 & SQL)
- **Backend Web & API** : `FastAPI`, `Uvicorn`, `Pydantic v2` (documentation OpenAPI 3 / Swagger interactive)
- **Frontend Web** : `React 19`, `Vite 8`, `Recharts 3.10`, `Lucide Icons`, Vanilla CSS avec Glassmorphism
- **Gestionnaire d'environnement & Tests** : Python `venv` (ou `uv`), `pytest`, `pytest-cov`, `responses`

---

## 3. Guide de Démarrage Rapide

### Prérequis
1. **Docker Desktop** opérationnel (pour le moteur PostgreSQL 16).
2. **Node.js** (`v18+`) et **npm**.
3. **Python 3.11+** (recommandé 3.13).

### Installation

1. **Variables d'environnement :**
   Initialisez votre fichier `.env` à partir du modèle fourni :
   ```bash
   copy .env.example .env
   ```

2. **Démarrer la base de données PostgreSQL :**
   ```bash
   docker compose up -d
   ```
   *(Le conteneur initialise automatiquement le schéma `gold`, les dimensions, les tables de faits et les vues via les scripts montés dans `sql/init/`)*.

3. **Backend & Pipeline (Python) :**
   ```bash
   # Création de l'environnement virtuel
   python -m venv .venv

   # Activation sous Windows (PowerShell) :
   .\.venv\Scripts\Activate.ps1
   # (Sous Linux / macOS : source .venv/bin/activate)

   # Installation des dépendances du projet
   pip install -e ".[dev]"
   ```

4. **Frontend (React) :**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

### Lancement de l'application

1. **Exécuter le pipeline de données complet (Bronze -> Silver -> Gold -> Qualité) :**
   ```bash
   .\.venv\Scripts\python -m src.energy_observatory.pipeline --stage all
   ```
   *(Collecte les 3 sources, assainit en Parquet, charge le modèle en étoile PostgreSQL et exécute les 10 contrôles de qualité en ~70 secondes)*.

2. **Démarrer le backend (API FastAPI) :**
   ```bash
   .\.venv\Scripts\python -m uvicorn src.energy_observatory.api.main:app --reload --port 8000
   ```
   Documentation interactive Swagger accessible sur **http://localhost:8000/docs**.

3. **Démarrer le frontend :**
   ```bash
   cd frontend
   npm run dev
   ```
   Accédez au tableau de bord web sur **http://localhost:5173**.

---

## 4. Les 3 Piliers de l'Architecture XamaleEnergy

---

### Pilier 1 — Le Pipeline Medallion & Assainissement Sémantique (`ingestion/` & `transformation/`)
Ce module regroupe l'ingestion résiliente, la traçabilité cryptographique et la réhabilitation physique des données :

1. **Ingestion streaming résiliente & Checksum SHA-256 (`ingestion/`)** :
   Télécharge les flux volumineux (~84 Mo pour RTE, ~41 Mo pour Enedis) par chunks continus de 64 Ko sans saturer la mémoire vive. Chaque extraction génère un hachage SHA-256 immuable et un fichier sidecar `metadata_*.json` (horodatage UTC, statut HTTP, volumétrie).
2. **Filtrage temporel strict & Résolution des auxiliaires (`rte_transform.py`)** :
   Isole les **257 105 mesures réelles** au pas 30 minutes en purgeant les prévisions au quart d'heure. Applique un *clamping* physique à `0.0 MW` sur les productions négatives nocturnes issues du soutirage d'auxiliaires des parcs photovoltaïques et thermiques.
3. **Typage strict & Quarantaine des rejets (`enedis_transform.py`)** :
   Préserve l'intégrité des codes géographiques INSEE (`01`, `2A`, `974`) sous forme de chaînes strictes. Exporte systématiquement les lignes non conformes dans `data/rejected/` avec le motif précis d'exclusion.
4. **Compression colonnaire Apache Parquet (Snappy)** :
   Convertit les données brutes (~125 Mo) au format Parquet optimisé (~17 Mo cumulés), assurant un **gain de stockage de x7.3** et des temps de lecture analytique ultra-rapides.

---

### Pilier 2 — Modélisation Star Schema & Moteur d'Audit Qualité (`storage/` & `quality/`)
Ce module structure les données pour l'analyse décisionnelle et certifie leur conformité scientifique :

1. **Modèle relationnel dimensionnel en étoile (Star Schema)** :
   - **Dimensions** : `dim_temps` (257k horodatages enrichis : heure, jour, mois, année, jour ouvré/week-end), `dim_geographie` (communes, départements, régions) et `dim_filiere` (11 technologies énergétiques).
   - **Faits** : `fact_electricite` (historique 30 min de production, consommation, solde et intensité carbone), `fact_registre` (125 885 installations raccordées) et `fact_worldbank` (série d'électrification).
2. **Vues analytiques haute performance** :
   - `gold.v_mix_energetique_mensuel` : agrégation pluriannuelle 2012–2026 précalculant la demande moyenne, les pointes et le taux de décarbonation.
   - `gold.v_capacites_par_region` : synthèse des puissances de production et stockage par région administrative.
3. **Moteur d'audit automatique à 10 règles (Score 100% PASS)** :
   Exécute 10 contrôles critiques à chaque chargement : continuité temporelle sans rupture (`TIME-01`), intégrité référentielle stricte (`REF-01` à `03`), équilibre physique du réseau ($\text{Production} + \text{Solde net} \approx \text{Consommation}$ sur `PHYS-01`), plausibilité des bornes physiques (`BOUND-01` et `02`), complétude (`NULL-01`) et cohérence internationale (`WB-01`).
4. **Édition de rapports certifiés** :
   Génération automatique de bilans d'intégrité horodatés exportés en formats **Markdown** et **JSON** dans `data/reports/`.

---

### Pilier 3 — L'API RESTful & Le Tableau de Bord Décisionnel (`api/` & `frontend/`)
Ce module expose les données certifiées et offre une expérience de visualisation réactive :

1. **API Backend modulaire FastAPI (Port 8000)** :
   Architecture REST structurée par routeurs indépendants (`metrics`, `mix`, `capacities`, `international`, `quality`, `health`) avec validation stricte via **Pydantic v2** et documentation OpenAPI 3 embarquée.
2. **Tableau de bord web React 19 (Port 5173)** :
   Interface moderne développée avec Vite et Recharts, reprenant l'identité visuelle de **XamaleEnergy** (*Midnight Deep Navy* `#050C18`, *Radiant Gold* `#F5B82E` et Glassmorphism) articulée autour de 5 modules :
   - **Temps Réel & Mix** : KPIs en direct, aires empilées par filière (30 min) et baromètre d'interconnexion avec 5 pays frontaliers.
   - **Historique Mensuel** : Séries longues 2012–2026, suivi des pointes hivernales et trajectoire de décarbonation.
   - **Registre & Capacités** : Cartographie de ~147 000 MW de capacités installées avec palmarès régional et filtres.
   - **Audit Qualité (10/10 PASS)** : Moniteur de conformité avec possibilité de relancer la validation en direct.
   - **Banque Mondiale** : Taux d'accès à l'électricité (1960–2025) documentant les valeurs manquantes.

---

## 5. API Backend & Frontend

- **`api/main.py`** : Serveur FastAPI haute performance qui distribue les données de la couche Gold vers le frontend via des routes typées (`/api/v1/metrics/latest`, `/api/v1/mix/history`, `/api/v1/mix/monthly`, `/api/v1/capacities/regional`, `/api/v1/quality/report`...).
- **`frontend/`** : Interface React 19 interactive connectée au backend, offrant une restitution visuelle instantanée des indicateurs énergétiques nationaux, des capacités régionales et du rapport d'audit qualité.
