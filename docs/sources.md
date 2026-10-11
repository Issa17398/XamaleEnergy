# Audit des Sources de Données — Observatoire Énergétique de la France

Document de référence établi dans le cadre de la **Phase 1 (Audit des sources)**.  
Toutes les informations présentées ci-dessous ont été **vérifiées en direct** auprès des API et métadonnées officielles de data.gouv.fr, d'ODRÉ (Open Data Réseaux Énergies) et de la Banque mondiale.

---

## Source A — RTE éCO2mix (National et Régional)

### 1. Rôle et périmètre métier
RTE (Réseau de Transport d'Électricité) publie via sa plateforme éCO2mix les chroniques de consommation et de production électrique française, ventilées par filière énergétique, ainsi que les échanges transfrontaliers physiques/commerciaux et l'estimation des émissions de CO2.

### 2. Ressources exactes identifiées

#### Volet National (Priorité Ingestion Phase 3)
- **Portail data.gouv.fr** : [donnees-eco2mix-nationales-consolidees-et-definitives](https://www.data.gouv.fr/datasets/donnees-eco2mix-nationales-consolidees-et-definitives)
- **ID data.gouv.fr** : `5afbd35fb595086a31734624`
- **Producteur & Hébergeur d'origine** : RTE / Open Data Réseaux Énergies (ODRÉ) sur OpenDataSoft
- **Identifiant dataset ODRÉ** : `eco2mix-national-cons-def`
- **URL export complet CSV (brut)** : `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/exports/csv?use_labels=true`
- **URL API REST v2.1** : `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/records`
- **Volume constaté** :
  - Nombre total de lignes : **514 272 enregistrements** (au 11/10/2026).
  - Taille du fichier CSV complet : **~83,8 Mo** (analyse data.gouv.fr : 83 850 793 octets).
- **Couverture temporelle** : Données définitives de janvier 2012 à décembre 2024, données consolidées depuis janvier 2021.
- **Granularité temporelle** :
  - **Pas 15 minutes (quart d'heure)** : Uniquement les prévisions de consommation J-1 (`prevision_j1`) et J (`prevision_j`). Les colonnes de réalisation (`consommation`, filières) y sont nulles.
  - **Pas 30 minutes (demi-heure)** : Consommation réalisée, production par filière, pompage, échanges, émissions CO2.
- **Fréquence de mise à jour** : Quotidienne (consolidation mensuelle à M+1, définitive à A+1).
- **Licence** : Licence Ouverte v2.0 (Etalab).

#### Volet Régional
- **Portail data.gouv.fr** : [donnees-eco2mix-regionales-consolidees-et-definitives](https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-consolidees-et-definitives)
- **Identifiant dataset ODRÉ** : `eco2mix-regional-cons-def`
- **Contrainte spécifique** : Un quota de 50 000 appels API/mois/utilisateur est actif sur l'endpoint unitaire ODRÉ en raison d'usages robotiques intensifs. L'export bulk CSV ou filtré par période doit être privilégié.

### 3. Schéma et dictionnaire des variables (éCO2mix National)

| Colonne source | Type observé | Unité | Description métier |
| :--- | :--- | :--- | :--- |
| `perimetre` | string | - | Toujours "France" pour le national |
| `nature` | string | - | Statut de validation ("Données définitives" ou "Données consolidées") |
| `date` | string (YYYY-MM-DD) | - | Date du calendrier |
| `heure` | string (HH:MM) | - | Heure légale française (ex: "13:30") |
| `date_heure` | string ISO-8601 | - | Timestamp avec offset UTC (ex: "2013-07-28T11:30:00+00:00") |
| `consommation` | int | MW | Consommation électrique brute réalisée |
| `prevision_j1` | int | MW | Prévision réalisée la veille pour le lendemain |
| `prevision_j` | int | MW | Prévision réactualisée le jour même |
| `fioul` | int | MW | Production thermique fioul |
| `charbon` | int | MW | Production thermique charbon |
| `gaz` | int | MW | Production thermique gaz |
| `nucleaire` | int | MW | Production nucléaire |
| `eolien` | int | MW | Production éolienne totale |
| `solaire` | int | MW | Production photovoltaïque |
| `hydraulique` | int | MW | Production hydroélectrique totale |
| `pompage` | int | MW | Puissance soutirée par les STEP (valeur négative ou nulle) |
| `bioenergies` | int | MW | Production des bioénergies (déchets, biomasse, biogaz) |
| `ech_physiques` | int | MW | Solde net des flux physiques aux frontières (<0 export, >0 import) |
| `taux_co2` | int | g/kWh | Intensité carbone de la production nationale d'électricité |
| `ech_comm_*` | int / text | MW | Échanges commerciaux par pays (Angleterre, Espagne, Italie, Suisse, Allemagne-Belgique) |
| Sous-filières détaillées | int / text | MW | TAC, cogénération, CCG, lacs, fil de l'eau, STEP turbinage... |

---

## Source B — Registre National des Installations de Production et de Stockage (Enedis / RTE / ELD)

### 1. Rôle et périmètre métier
Fournit la cartographie exhaustive des installations de production d'électricité (solaires, éoliennes, hydrauliques, etc.) et des installations de stockage raccordées aux réseaux de distribution (Enedis, ELD) et de transport (RTE).

### 2. Ressources exactes identifiées
- **Portail data.gouv.fr** : [registre-national-des-installations-de-production-et-de-stockage-delectricite-au-31-12-2025](https://www.data.gouv.fr/datasets/registre-national-des-installations-de-production-et-de-stockage-delectricite-au-31-12-2025)
- **ID data.gouv.fr** : `69c4af4e5c9f9567df414fc6`
- **Producteurs** : RTE, Enedis, EDF SEI, Entreprises Locales de Distribution (ELD).
- **Millésime vérifié** : **Arrêté au 31 décembre 2025**.
- **Identifiant dataset ODRÉ** : `registre-national-installation-production-stockage-electricite-agrege-311225`
- **URL export complet CSV** : `https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/registre-national-installation-production-stockage-electricite-agrege-311225/exports/csv?use_labels=true`
- **Volume constaté** :
  - Nombre total d'enregistrements : **125 930 lignes**.
  - Taille du fichier CSV complet : **~40,5 Mo** (Parquet disponible : ~4,76 Mo).
- **Règle réglementaire d'anonymisation / secret statistique** :
  - Les installations de puissance **inférieure à 36 kW** sont agrégées à la maille IRIS / commune (arrêté du 7 juillet 2016).
  - Le nom des propriétaires particuliers est anonymisé (`nominstallation: "privé"`).
- **Licence** : Licence Ouverte v2.0 (Etalab), badge HVD (High Value Dataset).

### 3. Schéma et principales variables

| Colonne source | Type observé | Unité / Format | Description |
| :--- | :--- | :--- | :--- |
| `codeeicresourceobject` | string | Code EIC | Identifiant européen de ressource / installation |
| `nominstallation` | string | Texte | Nom de la centrale ou mention "privé" |
| `codeinseecommune` / `commune`| string | Code INSEE / Libellé | Commune de rattachement |
| `codedepartement` / `departement` | string | Code / Libellé | Département |
| `coderegion` / `region` | string | Code / Libellé | Région administrative |
| `codeiris` | string | Code INSEE IRIS | Maille géographique statistique fine |
| `codefiliere` / `filiere` | string | Ex: "SOLAI" / "Solaire" | Filière de production |
| `codetechnologie` / `technologie`| string | Ex: "PHOTV" / "Photovoltaïque" | Technologie précise |
| `puismaxinstallee` | float | **kW** | Puissance maximale installée (capacité nominale) |
| `puismaxrac` | float | **kW** | Puissance maximale de raccordement |
| `tensionraccordement` | string | Ex: "BT", "HTA", "HTB" | Niveau de tension réseau |
| `datemiseenservice` | string (DD/MM/YYYY) | Date | Date de mise en service |
| `regime` | string | Ex: "En service" | Statut d'exploitation |
| `gestionnaire` | string | Ex: "ENEDIS", "GÉRÉDIS", "RTE" | Gestionnaire de réseau concédé |
| `energieannuelleglissanteinjectee` | int / float | kWh | Énergie annuelle glissante injectée sur le réseau |

> **Attention Métier Cruciale** : Ce registre recense des **capacités installées (kW)** et une énergie annuelle glissante indicative, mais **ne fournit pas une série temporelle de production instantanée** au pas horaire.

---

## Source C — Banque Mondiale (World Bank Open Data)

### 1. Rôle et périmètre métier
Fournir des indicateurs de contexte macro-énergétiques et de développement pour situer la France dans un cadre comparatif international.

### 2. Ressource exacte identifiée
- **Indicateur** : `EG.ELC.ACCS.ZS` — *Access to electricity (% of population)*
- **Endpoint API vérifié** :  
  `https://api.worldbank.org/v2/country/FRA/indicator/EG.ELC.ACCS.ZS?format=json&per_page=1000`
- **Format de réponse** : JSON composé d'une liste à deux éléments :
  1. Métadonnées de pagination (`page`, `pages`, `per_page`, `total`, `sourceid`, `lastupdated`).
  2. Tableau d'observations annuelles.
- **Volume et couverture constatés** :
  - Total : **66 points annuels** (de 1960 à 2025).
  - 1960–1989 : `value = null` (non mesuré / non disponible dans la série historique de la Banque mondiale).
  - 1990–2024 : `value = 100` (accès universel à 100,0 % en France).
  - 2025 : `value = null` (en attente de consolidation).
- **Fréquence de mise à jour** : Annuelle (dernière mise à jour de la source constatée : octobre 2026).
- **Licence** : Creative Commons Attribution 4.0 International (CC BY 4.0).

---

## Synthèse et Décisions d'Ingestion

| Source | Faisabilité Ingestion | Format brut cible | Stratégie recommandée |
| :--- | :--- | :--- | :--- |
| **Source A (RTE)** | **Validée** | CSV + JSON | Téléchargement incrémental / streaming CSV ou API par fenêtres annuelles/mensuelles |
| **Source B (Enedis)** | **Validée** | CSV (ou Parquet) | Téléchargement du millésime officiel 31/12/2025 (~40 Mo) avec snapshot Bronze horodaté |
| **Source C (World Bank)**| **Validée** | JSON | Appel API direct unitaire (très léger, 14 Ko), stocké en Bronze brut |
