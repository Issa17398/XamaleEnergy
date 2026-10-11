# Rapport d'Audit & Contrôle Qualité des Données — Couche Gold

> **Date de l'audit** : 2026-10-11T11:36:33.558229+00:00  
> **Statut Global** : 🟢 PASS (100% Conforme)  
> **Score de Conformité** : **100.00%**  
> **Durée d'analyse** : 0.59 s  

---

## 1. Synthèse Exécutive

| Métrique | Valeur |
|---|---|
| **Total des règles évaluées** | 10 |
| **Règles validées avec succès** | 10 |
| **Avertissements tolérés** | 0 |
| **Échecs critiques** | 0 |
| **Score Global de Qualité** | **100.00%** |

---

## 2. Tableau de Bord Détaillé des Contrôles

| ID | Catégorie | Règle / Contrôle | Statut | Résultat mesuré | Seuil attendu | Conclusion |
|---|---|---|---|---|---|---|
| `VOL-01` | Volumétrie & Typage | Volumétrie et couverture temporelle RTE | 🟢 PASS | `257105.0` | `250000.0` | 257,105 lignes détectées entre 2011-12-31 23:00:00+00:00 et 2026-08-31 21:30:00+00:00. |
| `TIME-01` | Complétude & Fraîcheur | Continuité temporelle (pas 30 minutes) | 🟢 PASS | `99.99416578505196` | `99.9` | Taux de continuité : 99.9942% (15 écarts temporels > 30 min sur 257,104 intervalles). |
| `REF-01` | Intégrité Référentielle | Intégrité référentielle Fact RTE -> Dim Temps | 🟢 PASS | `0.0` | `0.0` | Orphelins temporels détectés : 0. |
| `REF-02` | Intégrité Référentielle | Intégrité référentielle Fact Registre -> Dim Filière | 🟢 PASS | `0.0` | `0.0` | Installations sans filière valide : 0. |
| `REF-03` | Intégrité Référentielle | Intégrité référentielle Fact Registre -> Dim Géographie | 🟢 PASS | `0.0` | `0.0` | Codes INSEE non référencés dans la dimension géographique : 0. |
| `PHYS-01` | Cohérence Physique & Bilan Énergétique | Équilibre physique réseau (Consommation vs Injection nette) | 🟢 PASS | `0.932966720394425` | `2.0` | Écart médian réseau : 0.93% (seuil <= 2.0%). Écart moyen : 3.52% (pertes transport/distribution attendues 3-5%). Conformité tolérance 10% : 87.59%. |
| `BOUND-01` | Bornes Plausibles & Plages de Valeurs | Bornes physiques réalistes RTE (Conso, Nucléaire, CO2) | 🟢 PASS | `100.0` | `100.0` | 0 valeurs hors limites physiques sur 257,105 mesures. |
| `BOUND-02` | Bornes Plausibles & Plages de Valeurs | Plausibilité des capacités installées Enedis | 🟢 PASS | `100.0` | `100.0` | Capacités hors limites (> 0 kW et <= 2 GW) : 0/125,885. |
| `NULL-01` | Complétude & Fraîcheur | Complétude des métriques de production et consommation | 🟢 PASS | `0.0` | `0.0` | 0 valeurs nulles détectées sur les métriques clés de production et consommation. |
| `WB-01` | Bornes Plausibles & Plages de Valeurs | Cohérence indicateur Banque Mondiale (Accès électricité FRA) | 🟢 PASS | `66.0` | `66.0` | 66 observations annuelles, 0 valeurs aberrantes hors 90-100%. |

---

## 3. Analyse & Interprétations Métier des Données

### A. Continuité Temporelle & Volumétrie (RTE éCO2mix)
- **Période couverte** : 15 années consécutives (2012 à 2026).
- **Pas de temps** : 30 minutes réel (données définitives certifiées).
- **Complétude** : 99.994% de continuité temporelle sans interruption.

### B. Équilibre Physique & Pertes Réseau
- **Équilibre Injection / Soutirage** : En France, l'équation physique $P_{\text{conso}} \approx P_{\text{prod}} + P_{\text{import}} - P_{\text{pompage}}$ présente un écart médian de seulement **0.93%**.
- **Pertes en ligne RTE & Enedis** : L'écart moyen constaté est de **3.52%**, parfaitement aligné avec les pertes physiques en transport et distribution (3 à 5% selon la CRE).

### C. Intégrité Référentielle & Cohérence des Dimensions
- **Temps** : Zéro orphelin entre la table de faits RTE et la dimension `dim_temps`.
- **Filières** : 100% des 125 885 installations Enedis sont associées à une filière technologique normalisée.
- **Géographie** : 100% des communes avec code INSEE valide sont rattachées au référentiel administratif.

---
*Rapport généré automatiquement par l'Observatoire des Données Énergétiques de la France.*