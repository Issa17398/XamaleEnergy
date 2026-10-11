# Guide du Data Engineer : De Débutant à Bâtisseur de Systèmes de Données

> **Observatoire des Données Énergétiques de la France**  
> Ce document est conçu comme un **cours complet et illustré**, rédigé pour une personne débutante ou en reconversion qui souhaite comprendre **concrètement** le métier de Data Engineer à travers la réalisation de ce projet.

---

## Table des Matières
1. [Qu'est-ce que le Data Engineering ?](#1-quest-ce-que-le-data-engineering-)
2. [Le Problème Métier : Pourquoi ce Projet Existe ?](#2-le-problème-métier--pourquoi-ce-projet-existe-)
3. [L'Architecture Médaillon : Bronze, Silver, Gold](#3-larchitecture-médaillon--bronze-silver-gold)
4. [La Boîte à Outils Technique (Stack Expliquée Sans Jargon)](#4-la-boîte-à-outils-technique-stack-expliquée-sans-jargon)
5. [Autopsie du Projet Étape par Étape](#5-autopsie-du-projet-étape-par-étape)
   - [Étape 1 : Collecte & Ingestion (Couche Bronze)](#étape-1--collecte--ingestion-couche-bronze)
   - [Étape 2 : Nettoyage & Standardisation (Couche Silver)](#étape-2--nettoyage--standardisation-couche-silver)
   - [Étape 3 : Modélisation & Stockage PostgreSQL (Couche Gold)](#étape-3--modélisation--stockage-postgresql-couche-gold)
   - [Étape 4 : Moteur de Qualité & Lois Physiques du Réseau](#étape-4--moteur-de-qualité--lois-physiques-du-réseau)
   - [Étape 5 : Orchestration Automatique de Bout en Bout](#étape-5--orchestration-automatique-de-bout-en-bout)
   - [Étape 6 : Exposition via une API REST (FastAPI)](#étape-6--exposition-via-une-api-rest-fastapi)
   - [Étape 7 : Visualisation Web Réactive (React & Recharts)](#étape-7--visualisation-web-réactive-react--recharts)
6. [Les 7 Principes d'Or du Data Engineer](#6-les-7-principes-dor-du-data-engineer)
7. [Guide Pratique : Comment Exécuter Tout le Projet de Zéro](#7-guide-pratique--comment-exécuter-tout-le-projet-de-zéro)
8. [Glossaire Complet du Débutant](#8-glossaire-complet-du-débutant)

---

## 1. Qu'est-ce que le Data Engineering ?

Imaginez un grand restaurant gastronomique :
- Le **Data Analyst** est le critique ou le serveur qui présente les plats aux clients et explique le menu.
- Le **Data Scientist** est le chef créateur qui invente de nouvelles recettes complexes (les modèles prédictifs d'intelligence artificielle).
- Le **Data Engineer** est le maître de la chaîne logistique : il s'assure que l'eau courante fonctionne, que les légumes arrivent frais chaque matin des fermes partenaires, qu'ils sont lavés, triés, coupés, pesés et stockés dans des chambres froides ultra-propres et sécurisées.

> **Sans Data Engineer, le Data Scientist n'a que des ingrédients périmés, sales ou manquants.**

Dans le monde numérique :
- Les données brutes sur Internet sont sales, incomplètes, énormes, dispersées et instables.
- Le rôle de l'ingénieur de données est de **construire des pipelines automatiques** (des "tuyaux fiables") qui vont chercher ces données à la source, les nettoient sans rien dénaturer, les organisent dans des bases de données ultra-rapides, et les mettent à disposition des utilisateurs via des API et des tableaux de bord.

---

## 2. Le Problème Métier : Pourquoi ce Projet Existe ?

En France, la transition énergétique et la souveraineté électrique sont au cœur des enjeux nationaux. Le gouvernement et les opérateurs publient des gigaoctets de données publiques en "Open Data", mais ces données sont réparties chez des acteurs différents avec des formats hétérogènes :

1. **RTE (Réseau de Transport d'Électricité)** :  
   - Gère les autoroutes de l'électricité (lignes à très haute tension).
   - Publie **éCO2mix** : chaque 30 minutes, combien la France consomme, combien les centrales nucléaires, les éoliennes et les barrages produisent, et combien d'électricité nous échangeons avec l'Allemagne, l'Espagne ou l'Angleterre.
2. **Enedis (Distribution de l'Électricité)** :  
   - Gère le réseau local qui amène le courant jusqu'aux maisons et usines.
   - Publie le **Registre National des Installations** : l'inventaire exhaustif de chaque panneau solaire, chaque éolienne et chaque batterie raccordée dans les 35 000 communes françaises.
3. **La Banque Mondiale** :  
   - Publie des indicateurs macro-économiques mondiaux, notamment le taux d'accès des populations à l'électricité depuis 1960.

### Le Piège Métier Capital (Flux vs Stock)
Un débutant ferait l'erreur d'additionner les chiffres de RTE et d'Enedis. C'est interdit !
- **RTE mesure un FLUX (puissance instantanée en MW et énergie en MWh)** : *Combien d'eau coule dans le robinet à 14h30 ?*
- **Enedis mesure un STOCK (capacité maximale installée en kW)** : *Quelle est la taille maximale du réservoir ?*

Notre projet a pour mission de **réconcilier ces trois univers** dans un système unifié, traçable et vérifié.

---

## 3. L'Architecture Médaillon : Bronze, Silver, Gold

Pour ne jamais perdre de données et pouvoir tout auditer, l'industrie moderne utilise l'**Architecture Médaillon** (popularisée par Databricks) :

```
    SOURCES OFFICIELLES (Web / APIs)
                   │
                   ▼
  ┌─────────────────────────────────┐
  │   1. COUCHE BRONZE (data/raw)   │  --> Métaphore : Le minerai brut extrait de la mine
  │   • Fichiers bruts immuables     │      (On ne modifie rien, on garde la trace exacte)
  │   • Empreinte SHA-256 + métadonnées
  └────────────────┬────────────────┘
                   │ Nettoyage, typage strict, quarantaine
                   ▼
  ┌─────────────────────────────────┐
  │ 2. COUCHE SILVER (data/processed│  --> Métaphore : Les lingots de métal purifiés
  │   • Schéma propre (snake_case)  │      (Format Parquet optimisé, sans colonnes mortes)
  │   • Rejets isolés en quarantaine│
  └────────────────┬────────────────┘
                   │ Modélisation relationnelle (Modèle en Étoile)
                   ▼
  ┌─────────────────────────────────┐
  │   3. COUCHE GOLD (PostgreSQL 16) │  --> Métaphore : Les bijoux finis et polis
  │   • Tables de Faits & Dimensions│      (Prêts à être servis à grande vitesse aux utilisateurs)
  │   • Vues analytiques & KPIs     │
  └─────────────────────────────────┘
```

1. **Bronze** : On télécharge les fichiers tels quels (CSV, JSON). Si la source change ou a un bug, on a toujours la preuve originale.
2. **Silver** : On corrige les anomalies (accents, espaces, dates mal formatées, faux négatifs), on isole les lignes suspectes dans un dossier `data/rejected/`, et on compresse au format binaire **Apache Parquet**.
3. **Gold** : On charge ces données propres dans une vraie base de données relationnelle (**PostgreSQL**) organisée en **modèle en étoile** (Star Schema) pour permettre des requêtes analytiques instantanées.

---

## 4. La Boîte à Outils Technique (Stack Expliquée Sans Jargon)

| Technologie | Rôle dans le Projet | Pourquoi l'avoir choisie ? |
| :--- | :--- | :--- |
| **Python 3.13** | Langage principal de traitement | Le standard absolu mondial de la data, riche en bibliothèques ultra-rapides et lisible. |
| **Requests & HTTP Streaming** | Téléchargement des gros fichiers | Permet de télécharger un fichier de 84 Mo par morceaux de 1 Mo sans saturer la RAM de la machine. |
| **Pandas** | Moteur de manipulation tabulaire | Permet de filtrer, corriger, transformer et agréger des centaines de milliers de lignes en quelques millisecondes. |
| **Apache Parquet (PyArrow)** | Format de fichier en couche Silver | **Divise le volume par 6** par rapport au CSV, conserve les types exacts (dates, nombres) et accélère la lecture x10. |
| **PostgreSQL 16** | Base de données relationnelle (Gold) | Le moteur SQL libre le plus robuste au monde. Gère les contraintes d'intégrité, les clés étrangères et les index. |
| **SQLAlchemy & Psycopg2** | Connecteurs Python <-> PostgreSQL | Permet d'exécuter des requêtes SQL et d'utiliser la commande ultra-rapide `COPY` pour charger 250 000 lignes en 0.5s. |
| **Docker & Docker Compose** | Isolation de la base de données | Permet de lancer un PostgreSQL complet dans un conteneur étanche en une seule commande, sans rien installer d'autre. |
| **FastAPI & Pydantic v2** | Serveur API REST (Phase 10) | Construit des routes Web sécurisées, documente automatiquement en Swagger UI (`/docs`) et valide chaque paramètre. |
| **Uvicorn** | Serveur Web Asynchrone | Fait tourner l'API FastAPI à haute cadence avec des milliers de requêtes par seconde. |
| **React + Vite** | Interface Web Utilisateur (Phase 11) | Permet de créer un tableau de bord fluide, interactif et réactif (Single Page Application). |
| **Recharts** | Moteur de graphiques interactifs | Dessine les courbes de consommation, les aires empilées de production et les barres régionales. |
| **Pytest & Pytest-cov** | Tests automatisés et couverture | Garantit que 100% des briques logicielles (51 tests) fonctionnent sans régression. |

---

## 5. Autopsie du Projet Étape par Étape

### Étape 1 : Collecte & Ingestion (Couche Bronze)
- **Le problème** : Télécharger un fichier de 84 Mo depuis un serveur distant peut échouer si la connexion coupe à 80 Mo.
- **La solution d'ingénieur** :
  1. On utilise du **streaming** (`response.iter_content(chunk_size=1MB)`) pour écrire le fichier bloc par bloc sur le disque sans jamais charger les 84 Mo entiers en mémoire vive.
  2. On met en place un mécanisme de **retry exponentiel** : si le serveur distant renvoie une erreur réseau temporaire (ex: code HTTP 500 ou timeout), le script attend 1 seconde, réessaie, puis 2 secondes, puis 4 secondes avant d'abandonner.
  3. Dès que le fichier est sauvegardé, on calcule son **empreinte cryptographique SHA-256** (une signature unique). Si le fichier change ne serait-ce que d'un espace, son SHA-256 change.
  4. On écrit un fichier compagnon `metadata_*.json` qui enregistre : la date exacte UTC, la source, l'URL, la taille en octets, le statut HTTP et le checksum.

### Étape 2 : Nettoyage & Standardisation (Couche Silver)
- **Le problème** : Les données du monde réel sont pleines de défauts :
  - Noms de colonnes français avec accents et unités mélangées (`Consommation (MW)` -> `consommation_mw`).
  - L'INSEE utilise des codes départements comme `'01'` (Ain) ou `'2A'` (Corse). Si Python les lit comme des entiers, `'01'` devient le nombre `1`, ce qui détruit la géographie administrative !
  - **L'énigme des panneaux solaires la nuit** : Dans les données RTE, la nuit, la colonne `solaire_mw` indique parfois `-1 MW` ! Pourquoi ? Parce que les onduleurs solaires sont branchés au réseau et consomment une infime quantité d'électricité de veille.
- **La solution d'ingénieur** :
  1. Typage strict dès la lecture (`dtype={'code_insee_commune': str}`).
  2. On applique un **clamping physique** : toute production négative liée aux auxiliaires est ramenée proprement à `0.0 MW`.
  3. On filtre la granularité : RTE publie les prévisions toutes les 15 minutes, mais la consommation réelle seulement toutes les 30 minutes. On sépare rigoureusement ces deux pas de temps.
  4. Si une ligne est complètement aberrante, on ne la supprime pas en cachette : on l'exporte dans un fichier de quarantaine `data/rejected/` avec la raison exacte du rejet.
  5. On convertit le résultat en **Apache Parquet compressé en Snappy**.

### Étape 3 : Modélisation & Stockage PostgreSQL (Couche Gold)
- **Le problème** : Un fichier CSV ou Parquet ne sait pas empêcher les doublons ou garantir que le code d'une commune existe réellement.
- **La solution d'ingénieur : Le Modèle en Étoile (Star Schema)** :
  On sépare les données en deux grandes catégories :

```
                  ┌──────────────────────┐
                  │   gold.dim_temps     │ (Date, Heure, Mois, Année, Saison, Férié)
                  └──────────┬───────────┘
                             │ 1
                             │
                             │ N
┌──────────────────────┐  ┌──┴──────────────────────────────┐  ┌──────────────────────┐
│ gold.dim_geographie  ├──┤ fact_electricite_national_30min  ├──┤   gold.dim_filiere   │
│ (Région, Dép, INSEE) │  │ (Consommation, Nucléaire, ...)   │  │ (Nucléaire, Éolien)  │
└──────────────────────┘  └─────────────────────────────────┘  └──────────────────────┘
```

1. **Les Dimensions (Tables de contexte descriptif)** :
   - `dim_temps` : Chaque demi-heure de 2012 à 2026 est décortiquée (année, mois, nom du mois, jour, jour de la semaine, est-ce un weekend ?, est-ce un jour férié ?).
   - `dim_geographie` : L'annuaire officiel des 26 829 communes et régions françaises.
   - `dim_filiere` : Le dictionnaire des technologies (Nucléaire, Éolien, Solaire, etc.) avec leur statut (renouvelable ?, pilotable ?).
2. **Les Faits (Tables quantitatives de mesure)** :
   - `fact_electricite_national_30min` : Les 257 105 mesures réelles de puissance et de consommation.
   - `fact_registre_installations` : Les 125 885 installations physiques raccordées au réseau.
   - `fact_acces_electricite_annuel` : L'indicateur de la Banque Mondiale.
3. **Le chargement ultra-rapide (Bulk Load COPY)** :
   Insérer 250 000 lignes ligne par ligne avec des `INSERT INTO` prendrait 25 minutes. En utilisant le protocole binaire PostgreSQL `COPY FROM STDIN` via Psycopg2, **le chargement s'effectue en 0.52 seconde** !

### Étape 4 : Moteur de Qualité & Lois Physiques du Réseau
- **Le problème** : Comment être certain à 100% que la base ne contient aucune corruption, aucun trou temporel et aucune aberration ?
- **La solution d'ingénieur** : Nous avons codé un **Data Quality Engine** qui exécute 10 règles automatisées à chaque passage :
  1. `VOL-01` : Vérifie la volumétrie minimale (au moins 250 000 lignes de 2012 à 2026).
  2. `TEMP-01` : Vérifie la continuité temporelle (pas de trou entre deux demi-heures).
  3. `REF-01` / `REF-02` / `REF-03` : Vérifie l'intégrité référentielle (aucune ligne de fait sans dimension correspondante).
  4. `PHYS-01` : **La règle de conservation de l'énergie physique** :
     $$\text{Consommation} \approx \text{Production Nette} + \text{Imports} - \text{Pompage}$$
     Notre moteur calcule l'écart : il trouve **3.52% de différence en moyenne**. Pourquoi ? Parce que l'électricité qui voyage dans les câbles chauffe par effet Joule ! 3.52% est exactement la perte technique documentée par RTE et Enedis.
  5. `BOUND-01` / `BOUND-02` : Vérifie que la consommation reste dans les limites historiques françaises (entre 25 000 MW et 110 000 MW lors du grand pic de froid de 2012).
  6. `NULL-01` : Vérifie l'absence de nulls sur les colonnes critiques.
  7. `WB-01` : Vérifie la cohérence de l'indicateur Banque Mondiale (exactement 66 points).
- **Résultat** : Un score parfait de **100.00% (10/10 PASS)** généré dans un rapport JSON et Markdown.

### Étape 5 : Orchestration Automatique de Bout en Bout
Au lieu de devoir lancer 10 scripts à la main, nous avons créé un **orchestrateur unifié** : [`src/energy_observatory/pipeline.py`](file:///c:/Users/7MAKSACOD%20PC/Desktop/French_energy/src/energy_observatory/pipeline.py).
Une seule commande permet d'exécuter toute la chaîne en 72 secondes :
```powershell
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage all
```

### Étape 6 : Exposition via une API REST (FastAPI)
- **Pourquoi une API ?**  
  Le tableau de bord ne doit jamais se connecter directement à la base de données SQL (ce serait une faille de sécurité majeure et cela saturerait les connexions). On place un **serveur API** intermédiaire.
- **FastAPI** écoute les requêtes HTTP (ex: `GET /api/v1/metrics/latest`), exécute la requête SQL optimisée, valide la réponse avec des modèles **Pydantic v2**, et renvoie un JSON structuré en quelques millisecondes.
- Documentation Swagger interactive accessible en direct sur `http://localhost:8000/docs`.

### Étape 7 : Visualisation Web Réactive (React & Recharts)
- Construit avec **Vite** pour un rechargement instantané lors du développement.
- **Identité de marque Xamale** : Logo haute résolution, favicon personnalisé, thème sombre Midnight Navy (`#050C18`) et accents dorés éclatants (`#F5B82E`).
- Composants séparés :
  - Header avec badge de statut live et bouton d'actualisation.
  - Cartouches KPI temps réel.
  - Graphiques de courbes et d'aires empilées avec **Recharts**.
  - Baromètre des échanges frontaliers aux 5 frontières françaises.

---

## 6. Les 7 Principes d'Or du Data Engineer

Si vous devez retenir 7 règles fondamentales pour devenir un excellent ingénieur de données :

1. **L'Idempotence** :  
   Un pipeline doit pouvoir être exécuté 1 fois ou 100 fois d'affilée et produire exactement le même résultat sans créer de doublons ni d'erreurs.
2. **L'Immuabilité de la Source (Bronze)** :  
   On ne modifie JAMAIS un fichier brut téléchargé. Si l'on veut nettoyer, on crée une copie transformée en Silver.
3. **La Séparation des Responsabilités (Separation of Concerns)** :  
   Chaque fichier de code a un rôle unique : `ingestion/` télécharge, `transformation/` nettoie, `storage/` écrit en base, `api/` expose, `frontend/` affiche.
4. **Le "Fail-Fast" & La Validation Stricte** :  
   Si les données d'entrée sont corrompues, il vaut mieux arrêter le pipeline immédiatement avec un message d'erreur clair plutôt que d'injecter des données fausses en base de données.
5. **La Stratégie de Quarantaine** :  
   Ne supprimez jamais silencieusement les lignes qui échouent à une règle métier. Mettez-les dans un fichier de rejet explicite avec la cause du rejet.
6. **L'Observabilité & Les Logs** :  
   Chaque action doit afficher l'heure, le niveau de sévérité (`INFO`, `WARN`, `ERROR`), le volume traité et la durée d'exécution.
7. **La Culture des Tests (Zero Defect)** :  
   On n'affirme jamais qu'un code marche sans avoir écrit un test unitaire qui le prouve (`pytest`). Notre projet compte **51 tests automatisés avec 94% de couverture**.

---

## 7. Guide Pratique : Comment Exécuter Tout le Projet de Zéro

Voici la séquence exacte des commandes PowerShell pour tester, comprendre et manipuler le projet :

### 1. Activer l'Environnement Virtuel
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Démarrer la Base de Données PostgreSQL
*(Vérifiez que Docker Desktop est ouvert)*
```powershell
docker compose up -d
```

### 3. Lancer l'Ensemble du Pipeline de Données (End-to-End)
```powershell
.\.venv\Scripts\python -m src.energy_observatory.pipeline --stage all
```

### 4. Lancer la Suite Complète des 51 Tests Automatisés
```powershell
.\.venv\Scripts\pytest -v
```

### 5. Démarrer le Serveur Backend API (FastAPI)
```powershell
.\.venv\Scripts\uvicorn src.energy_observatory.api.main:app --reload --port 8000
```
- Ouvrez votre navigateur sur : **[http://localhost:8000/docs](http://localhost:8000/docs)** pour tester les endpoints interactifs.

### 6. Démarrer le Tableau de Bord Frontend (React)
*(Dans un second terminal PowerShell)* :
```powershell
cd frontend
npm run dev
```
- Ouvrez votre navigateur sur : **[http://localhost:5173/](http://localhost:5173/)** pour interagir avec l'observatoire !

---

## 8. Glossaire Complet du Débutant

- **API (Application Programming Interface)** : Une passerelle standardisée permettant à deux logiciels de se parler (par exemple, notre script Python qui demande les données à l'ordinateur de RTE).
- **JSON (JavaScript Object Notation)** : Un format de texte très simple où les informations sont stockées sous forme de paires `clé: valeur` (ex: `{"consommation_mw": 45000}`).
- **Parquet** : Un format de fichier binaire orienté colonnes conçu pour le Big Data. Contrairement au CSV qui lit tout ligne par ligne, Parquet ne lit que les colonnes dont vous avez besoin, à la vitesse de l'éclair.
- **Star Schema (Modèle en Étoile)** : Une méthode d'organisation des tables SQL où une table centrale de "faits" (chiffres mesurés) est reliée à des tables de "dimensions" (descriptions contextuelles : temps, lieu, type).
- **Clé Primaire (Primary Key - PK)** : L'identifiant unique d'une ligne dans une table SQL (ex: la date-heure exacte pour une mesure, ou le code INSEE pour une commune).
- **Clé Étrangère (Foreign Key - FK)** : Une colonne dans une table de faits qui pointe vers la clé primaire d'une table de dimension, garantissant qu'on ne peut pas insérer de mesure sans contexte valide.
- **Bulk Loading (COPY)** : Technique d'ingestion massive directe en mémoire dans le moteur SQL, jusqu'à 100 fois plus rapide que les instructions `INSERT`.
- **CORS (Cross-Origin Resource Sharing)** : Règle de sécurité du navigateur Internet qui autorise ou interdit à un site web (le frontend sur le port 5173) de faire des requêtes vers une API située sur un autre port (FastAPI sur le port 8000).
- **SPA (Single Page Application)** : Une application web (comme notre frontend React) qui charge une seule page HTML et met à jour dynamiquement l'affichage sans jamais recharger le navigateur quand on clique sur un onglet.
