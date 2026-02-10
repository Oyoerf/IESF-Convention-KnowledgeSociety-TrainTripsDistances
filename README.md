# Pipeline de Traitement des Billets SNCF

Pipeline complet pour l'extraction et l'analyse des données de trajets SNCF à partir de justificatifs PDF.

## 📋 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

## 🔧 Installation

1. Installer les dépendances :

```bash
pip install -r requirements.txt
```

Ou avec pip3 :

```bash
pip3 install -r requirements.txt
```

## 📁 Structure des fichiers

Le pipeline nécessite les fichiers suivants :

- `main.py` - Script principal
- `PdfParserTickets.py` - Extraction des références depuis PDF
- `Extract_SNCF_Trips_v5.py` - Extraction des trajets via API SNCF
- `Duplicate_Manager_Excel.py` - Suppression des doublons
- `cities_to_GPS_cache_v2.py` - Géocodage des villes
- `Verifications_Trajets_v1.py` - Vérifications de cohérence
- `signal_batch_distances_V3.py` - Calcul des distances

## 📂 Organisation des données d'entrée

Créer une structure de dossiers comme suit :

```
./billets/
├── billets-train-WE1/
│   ├── justificatif1.pdf
│   ├── justificatif2.pdf
│   └── ...
├── billets-train-WE2/
│   ├── justificatif1.pdf
│   └── ...
├── billets-train-WE3/
│   └── ...
└── billets-train-WE4/
    └── ...
```

**Important** : 
- Les noms des sous-dossiers doivent suivre le pattern `billets-train-XXX` où `XXX` sera utilisé comme identifiant de l'évènement
- Le pipeline **détecte automatiquement** tous les sous-dossiers présents
- Vous pouvez avoir 1, 2, 3, 4 ou plus de weekends
- Les noms peuvent être `WE1`, `WE2`, `Weekend1`, `Jan2025`, etc. (toute chaîne après le 2e tiret)

## 🚀 Utilisation

Lancer le pipeline complet :

```bash
python main.py
```

Ou avec python3 :

```bash
python3 main.py
```

## 📊 Étapes du pipeline

Le pipeline exécute 6 étapes séquentiellement :

### Étape 1 : Extraction des références SNCF depuis les PDF
- **Entrée** : Fichiers PDF dans `./billets/billets-train-XXX/`
- **Sortie** : `voyageurs_sncf_XXX.xlsx` (un par sous-dossier détecté)
- **Contenu** : Nom, Prénom, Référence SNCF
- **Note** : Le pipeline détecte automatiquement tous les sous-dossiers présents. Le programme peut détecter les informations des billets SNCF Connect, INOUI et SNCF Voyageurs. Attention, il y a des erreurs dans le cas des personnes avec un nom ou prénom composé (le dernier mot du nom complet du voyageur est considéré comme le nom de famille).

### Étape 2 : Récupération des informations de trajet
- **Entrée** : `voyageurs_sncf_XXX.xlsx`
- **Sortie** : `trajets_XXX_raw.xlsx`
- **Contenu** : Détails des trajets via API SNCF.

### Étape 3 : Suppression des doublons
- **Entrée** : `trajets_XXX_raw.xlsx`
- **Sortie** : `trajets_XXX_deduplicated.xlsx`
- **Action** : Supprime les trajets en double entre différentes références

### Étape 4 : Conversion des villes en coordonnées GPS
- **Entrée** : `trajets_XXX_deduplicated.xlsx`
- **Sortie** : `trajets_XXX_with_gps.xlsx`
- **Action** : Ajoute latitude/longitude pour chaque ville
- **Cache** : `geocoding_cache.xlsx` (réutilisé entre exécutions, et fourni dans le fossier GitHub). Certaines géolocalisations fonctionnent mal, par exemple pour Strabsourg, il y a plusieurs coordonnées GPS correspondantes. La coordonnée qui fonctionne est incluse dans le fichier 'geocoding_cache.xlsx"

### Étape 5 : Ajout des vérifications
- **Entrée** : `trajets_XXX_with_gps.xlsx`
- **Sortie** : `trajets_XXX_verified.xlsx`
- **Action** : Ajoute colonnes de vérification (trajets pairs, circuits), afin de faciliter l'audit des trajets proposés. Il est RECOMMANDÉ d'ouvrir ce fichier excel afin de vérifier manuellement la pertinence des trajets détectés. Un cache "trip_cache.json" est créé, qui associe une clé unique à chaque trajet (une clé pour tous les Paris-Nantes, une clé pour tous les Aix-Marseille, etc.), afin d'éviter de multiplier les requêtes API inutiles et accélérer le processus.

### Étape 6 : Calcul des distances et rapport final
- **Entrée** : `trajets_XXX_verified.xlsx`
- **Sortie** : `rapport_final_XXX.xlsx` ✅ **FICHIER FINAL**
- **Action** : Calcule les distances réelles et génère le rapport

## 📄 Fichiers de sortie

### Fichiers finaux :
- Un fichier `rapport_final_XXX.xlsx` pour chaque weekend détecté
- Exemples : `rapport_final_WE1.xlsx`, `rapport_final_WE2.xlsx`, etc.

### Fichiers intermédiaires (conservés pour audit) :

Pour chaque weekend détecté (nombre variable selon vos dossiers) :
- `voyageurs_sncf_XXX.xlsx` - Étape 1
- `trajets_XXX_raw.xlsx` - Étape 2
- `trajets_XXX_deduplicated.xlsx` - Étape 3
- `trajets_XXX_with_gps.xlsx` - Étape 4
- `trajets_XXX_verified.xlsx` - Étape 5 -> A VÉRIFIER MANUELLEMENT POUR S'ASSURER DE LA COHÉRENCE DES TRAJETS

### Fichier de cache :
- `geocoding_cache.xlsx` - Cache des coordonnées GPS (partagé)

## ⏱️ Temps d'exécution estimé

Pour 4 weekends :

- Étape 1 : ~1-2 minutes (selon nombre de PDF)
- Étape 2 : ~2-5 minutes (appels API SNCF avec délai de 0.5s entre chaque) -> NE PAS DIMINUER CETTE VALEUR POUR RESTER POLI AVEC LE SERVEUR ET ÉVITER UN BAN AUTOMATIQUE
- Étape 3 : ~10-30 secondes
- Étape 4 : ~1-3 minutes (premier lancement), ~10-30 secondes (avec cache)
- Étape 5 : ~10-30 secondes
- Étape 6 : ~1-2 minutes  -> IDEM, NE PAS DIMINUER LA VALEUR DE "sleep" POUR RESTER POLI AVEC LE SERVEUR ENTRE CHAQUE REQUÊTE

**Total estimé** : 5-15 minutes pour 4 weekends

⚠️ Le temps varie selon le nombre de sous-dossiers détectés dans `./billets/`

## 🔍 Suivi de la progression

Le script affiche en temps réel :
- L'étape en cours (X/6)
- Les fichiers traités
- Les fichiers générés (avec ✓)
- Les éventuelles erreurs ou avertissements
- Un récapitulatif final avec durée totale

## ⚠️ Gestion des erreurs

Si une étape échoue :
- Le message d'erreur indique l'étape et la raison
- Les fichiers intermédiaires déjà créés sont conservés
- Le pipeline s'arrête pour permettre le débogage

## 💡 Conseils

1. **Premier lancement** : Le géocodage (Étape 4) sera plus long car il construit le cache
2. **Lancements suivants** : Le cache GPS accélère considérablement l'Étape 4
3. **Vérification** : Consultez les fichiers intermédiaires en cas de doute sur les données
4. **API SNCF** : Respecte automatiquement les délais entre requêtes (0.5s)

## 📞 Dépannage

### "Fichier introuvable"
- Vérifiez que le dossier `./billets` existe
- Vérifiez la structure des sous-dossiers (`billets-WE-XXX`)

### "Aucune donnée extraite"
- Vérifiez que les PDF contiennent bien des justificatifs SNCF valides
- Vérifiez le format des PDF (doivent être lisibles par pdfplumber)

### Erreurs API SNCF
- Vérifiez votre connexion Internet
- Les références SNCF dans les PDF doivent être valides et actuelles

### Erreurs de géocodage
- Nécessite une connexion Internet pour les trajets non présents dans le cache fourni
- Utilise le service gratuit OpenStreetMap (Nominatim)
- Respecte automatiquement les limites de taux (1s entre requêtes API) NE PAS DIMINUER CETTE VALEUR

### Erreur lors des requêtes SNCF Voyageurs
- Les billets trop anciens (plus de 2 à 3 mois) sont supprimés de leur serveur par la SNCF, donc il est recommandé d'utiliser ce programme pour des trajets récents !