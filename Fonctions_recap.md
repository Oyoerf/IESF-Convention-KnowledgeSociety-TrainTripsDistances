# RÉCAPITULATIF DES FONCTIONS UTILISÉES

Ce document liste TOUTES les fonctions appelées dans le main.py et leur origine exacte.

## Structure du pipeline

```
./billets/
├── billets-WE-WE1/  (PDFs)
├── billets-WE-WE2/  (PDFs)
├── billets-WE-WE3/  (PDFs)
└── billets-WE-WE4/  (PDFs)
```

## ÉTAPE 1 : Extraction des références SNCF

**Script** : `PdfParserTickets.py`  
**Fonction appelée** : `iterate_through_folders(root_dir)`

**Paramètres** :
- `root_dir` (str) : `"./billets"`

**Sorties générées** :
- `voyageurs_sncf_WE1.xlsx`
- `voyageurs_sncf_WE2.xlsx`
- `voyageurs_sncf_WE3.xlsx`
- `voyageurs_sncf_WE4.xlsx`

**Colonnes des fichiers de sortie** :
- `Nom` : Nom de famille du voyageur
- `Prenom` : Prénom du voyageur
- `Ref` : Référence SNCF

---

## ÉTAPE 2 : Extraction des trajets via API SNCF

**Script** : `Extract_SNCF_Trips_v5.py`  
**Fonction appelée** : `extract_sncf_trips(input_file, output_file, supprimer_doublons_flag)`

**Paramètres pour chaque WE** :
- `input_file` (str) : `f'voyageurs_sncf_{we}.xlsx'`
- `output_file` (str) : `f'trajets_{we}_raw.xlsx'`
- `supprimer_doublons_flag` (bool) : `False` (on gère ça à l'étape suivante)

**Sorties générées** :
- `trajets_WE1_raw.xlsx`
- `trajets_WE2_raw.xlsx`
- `trajets_WE3_raw.xlsx`
- `trajets_WE4_raw.xlsx`

**Colonnes des fichiers de sortie** :
- `Nom` : Nom de famille
- `Prenom` : Prénom
- `Reference` : Référence SNCF
- `Depart` : Ville de départ
- `Destination` : Ville d'arrivée
- `Type de train` : Type de train (TGV INOUI, TER, etc.)

---

## ÉTAPE 3 : Suppression des doublons

**Script** : `Duplicate_Manager_Excel.py`  
**Fonction appelée** : `supprimer_doublons_trajets(fichier_entree, fichier_sortie)`

**Paramètres pour chaque WE** :
- `fichier_entree` (str) : `f'trajets_{we}_raw.xlsx'`
- `fichier_sortie` (str) : `f'trajets_{we}_deduplicated.xlsx'`

**Sorties générées** :
- `trajets_WE1_deduplicated.xlsx`
- `trajets_WE2_deduplicated.xlsx`
- `trajets_WE3_deduplicated.xlsx`
- `trajets_WE4_deduplicated.xlsx`

**Logique** :
- Conserve tous les trajets d'une même référence (même les aller-retour)
- Supprime les trajets qui existent déjà sous une autre référence pour la même personne

---

## ÉTAPE 4 : Conversion villes → GPS

**Script** : `cities_to_GPS_cache_v2.py`  
**Fonction appelée** : `excel_cities_to_gps(input_file, output_file, cache_file, city_columns)`

**Paramètres pour chaque WE** :
- `input_file` (str) : `f'trajets_{we}_deduplicated.xlsx'`
- `output_file` (str) : `f'trajets_{we}_with_gps.xlsx'`
- `cache_file` (str) : `"geocoding_cache.xlsx"` (partagé entre tous les WE)
- `city_columns` (list) : `['Depart', 'Destination']`

**Sorties générées** :
- `trajets_WE1_with_gps.xlsx`
- `trajets_WE2_with_gps.xlsx`
- `trajets_WE3_with_gps.xlsx`
- `trajets_WE4_with_gps.xlsx`
- `geocoding_cache.xlsx` (cache partagé)

**Colonnes ajoutées** :
- `Depart_Latitude` : Latitude du départ
- `Depart_Longitude` : Longitude du départ
- `Destination_Latitude` : Latitude de la destination
- `Destination_Longitude` : Longitude de la destination

**Optimisation** :
- Utilise le cache pour éviter les requêtes répétées
- Normalise les noms de villes (majuscules, sans tirets)
- Ignore les entrées "not found"

---

## ÉTAPE 5 : Ajout des vérifications

**Script** : `Verifications_Trajets_v1.py`  
**Fonction appelée** : `ajouter_verifications_simple(fichier_entree, fichier_sortie)`

**Paramètres pour chaque WE** :
- `fichier_entree` (str) : `f'trajets_{we}_with_gps.xlsx'`
- `fichier_sortie` (str) : `f'trajets_{we}_verified.xlsx'`

**Sorties générées** :
- `trajets_WE1_verified.xlsx`
- `trajets_WE2_verified.xlsx`
- `trajets_WE3_verified.xlsx`
- `trajets_WE4_verified.xlsx`

**Colonnes ajoutées** :
- `Nb trajets pair?` : "PAIR" ou "IMPAIR" (coloré en rouge si impair)
- `Trajet circulaire?` : "OUI" ou "NON" (coloré selon le résultat)

**Vérifications effectuées** :
1. Nombre de trajets pair pour chaque personne (devrait être pair)
2. Premier départ = dernière arrivée (trajet circulaire)

---

## ÉTAPE 6 : Calcul des distances

**Script** : `signal_batch_distances_V3.py`  
**Fonction appelée** : `process_excel(input_file, output_file, cache_file)`

**Paramètres pour chaque WE** :
- `input_file` (str) : `f'trajets_{we}_verified.xlsx'`
- `output_file` (str) : `f'rapport_final_{we}.xlsx'`
- `cache_file` (str) : `"trip_cache.json"` (partagé entre tous les WE)

**Sorties générées** :
- `rapport_final_WE1.xlsx` ✅ **FICHIER FINAL**
- `rapport_final_WE2.xlsx` ✅ **FICHIER FINAL**
- `rapport_final_WE3.xlsx` ✅ **FICHIER FINAL**
- `rapport_final_WE4.xlsx` ✅ **FICHIER FINAL**
- `trip_cache.json` (cache partagé)

**Colonnes ajoutées** :
- `distance_km` : Distance totale du trajet en km
- `lgv_km` : Distance sur lignes à grande vitesse (LGV)
- `ter_km` : Distance sur lignes classiques (TER)
- `unknown_km` : Distance sur lignes non identifiées
- `lgv_pct` : Pourcentage de LGV (%)
- `ter_pct` : Pourcentage de TER (%)

**API utilisée** :
- Signal API (https://signal.eu.org/osm/eu/route/v1/train)
- Calcul d'itinéraires ferroviaires réels
- Délai de 1 seconde entre chaque appel API

**Optimisation** :
- Traite uniquement les trajets uniques
- Utilise le cache pour éviter les requêtes répétées
- Normalisation des noms de villes identique au géocodage

---

## RÉSUMÉ DES IMPORTS

```python
from PdfParserTickets import iterate_through_folders
from Extract_SNCF_Trips_v5 import extract_sncf_trips
from Duplicate_Manager_Excel import supprimer_doublons_trajets
from cities_to_GPS_cache_v2 import excel_cities_to_gps
from Verifications_Trajets_v1 import ajouter_verifications_simple
from signal_batch_distances_V3 import process_excel
```

---

## FICHIERS DE CACHE PARTAGÉS

### 1. `geocoding_cache.xlsx`
- **Utilisé par** : Étape 4 (cities_to_GPS_cache_v2.py)
- **Format** : Excel
- **Colonnes** : `city_name`, `latitude`, `longitude`
- **Persiste** : Entre les exécutions du pipeline
- **Avantage** : Évite de re-géocoder les mêmes villes

### 2. `trip_cache.json`
- **Utilisé par** : Étape 6 (signal_batch_distances_V3.py)
- **Format** : JSON
- **Structure** : Hash MD5 → résultats de trajet
- **Persiste** : Entre les exécutions du pipeline
- **Avantage** : Évite de recalculer les mêmes trajets

---

## TOTAL DES FICHIERS GÉNÉRÉS

### Par weekend (×4) :
- 6 fichiers intermédiaires
- 1 fichier final

### Partagés :
- 2 fichiers de cache

### TOTAL : 4 × 7 + 2 = **30 fichiers**

---

## TEMPS D'EXÉCUTION ESTIMÉ

| Étape | Temps (1er lancement) | Temps (avec cache) |
|-------|----------------------|-------------------|
| 1. Extraction PDF | 1-2 min | 1-2 min |
| 2. API SNCF | 2-5 min | 2-5 min |
| 3. Déduplication | 10-30 sec | 10-30 sec |
| 4. Géocodage | 1-3 min | 10-30 sec ⚡ |
| 5. Vérifications | 10-30 sec | 10-30 sec |
| 6. Distances | 3-5 min | 30 sec-1 min ⚡ |
| **TOTAL** | **8-16 min** | **5-10 min** |

---

## DÉPENDANCES EXTERNES
NE PAS DIMINUER LE DÉLAIS ENTRE LES REQUETES API !! (risques de surcharge des serveurs, ou de ban automatique)
### APIs utilisées :
1. **SNCF Voyageurs API** (Étape 2)
   - `https://www.sncf-voyageurs.com/api/pao/orders/`
   - `https://www.sncf-voyageurs.com/api/pao/pdf/`
   - Délai : 0.5 seconde entre requêtes

2. **OpenStreetMap Nominatim** (Étape 4)
   - Service de géocodage gratuit
   - Délai : 1 seconde entre requêtes

3. **Signal API** (Étape 6)
   - `https://signal.eu.org/osm/eu/route/v1/train`
   - Calcul d'itinéraires ferroviaires
   - Délai : 1 seconde entre requêtes

### Bibliothèques Python :
- `pandas` : Manipulation Excel
- `openpyxl` : Lecture/écriture Excel
- `pdfplumber` : Extraction PDF
- `geopy` : Géocodage
- `requests` : Appels HTTP