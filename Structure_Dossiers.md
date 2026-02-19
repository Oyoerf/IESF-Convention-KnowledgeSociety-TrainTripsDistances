# STRUCTURE DES DOSSIERS - GUIDE COMPLET

## ✅ Structure correcte

Le pipeline **détecte automatiquement** tous les sous-dossiers qui suivent le pattern `billets-train-XXX`.

### Exemple avec identifiants personnalisés :

```
./billets/
├── billets-train-Bordeaux/     ← Détecté → crée voyageurs_sncf_Bordeaux.xlsx
│   └── tickets.pdf
│
├── billets-train-Lyon/         ← Détecté → crée voyageurs_sncf_Lyon.xlsx
│   └── billets.pdf
│
└── billets-train-Paris/        ← Détecté → crée voyageurs_sncf_Paris.xlsx
    └── justificatifs.pdf
```

## 🔑 Règles de nommage

### Pattern obligatoire : `billets-train-{IDENTIFIANT}`

- ✅ **1er mot** : `billets` (obligatoire)
- ✅ **2e mot** : `WE` (obligatoire)
- ✅ **3e mot** : `{IDENTIFIANT}` (votre choix, sera utilisé dans les noms de fichiers)

### Exemples valides :

| Nom du dossier | Identifiant extrait | Fichier créé |
|----------------|---------------------|--------------|
| `billets-train-WE1` | `WE1` | `voyageurs_sncf_WE1.xlsx` |
| `billets-train-Weekend1` | `Weekend1` | `voyageurs_sncf_Weekend1.xlsx` |
| `billets-train-Jan2025` | `Jan2025` | `voyageurs_sncf_Jan2025.xlsx` |
| `billets-train-Paris` | `Paris` | `voyageurs_sncf_Paris.xlsx` |
| `billets-train-Test123` | `Test123` | `voyageurs_sncf_Test123.xlsx` |

### ❌ Exemples INVALIDES :

| Nom du dossier | Problème |
|----------------|----------|
| `billets-train1` | ❌ Manque un tiret (devrait être `billets-train-WE1`) |
| `WE-WE1` | ❌ Ne commence pas par `billets` |
| `billets_WE_WE1` | ❌ Utilise des underscores au lieu de tirets |
| `billets-train-` | ❌ Pas d'identifiant après le 2e tiret |
| `PDF-WE-WE1` | ❌ Ne commence pas par `billets` |

## 📋 Comment le pipeline traite les dossiers

### Code d'extraction (dans TicketsParser.py) :

```python
for subdir in root_path.iterdir():
    if subdir.is_dir():
        name = subdir.name.split('-')[2]  # Extrait le 3e élément
        output_file = f'voyageurs_sncf_{name}.xlsx'
```

### Exemple de traitement :

```
Dossier : "billets-train-WE1"
Split('-') : ["billets", "WE", "WE1"]
Index [2] : "WE1"
Fichier : "voyageurs_sncf_WE1.xlsx"
```

## 🔄 Flux complet pour un dossier

```
./billets/billets-train-WE1/
    ├── justif1.pdf
    └── justif2.pdf
         ↓
    Étape 1
         ↓
voyageurs_sncf_WE1.xlsx
         ↓
    Étape 2
         ↓
trajets_WE1_raw.xlsx
         ↓
    Étape 3
         ↓
trajets_WE1_deduplicated.xlsx
         ↓
    Étape 4
         ↓
trajets_WE1_with_gps.xlsx
         ↓
    Étape 5
         ↓
trajets_WE1_verified.xlsx
         ↓
    Étape 6
         ↓
rapport_final_WE1.xlsx ✅
```

## 📁 Contenu des fichiers PDF

Les PDF doivent être des **billets de train SNCF** contenant :

### Informations extraites :
- ✅ Référence du dossier (format : `Réf: XXXXXX`)
- ✅ Nom du voyageur 1 (format : `Voyageur 1 : PRENOM NOM`)

### Formats supportés :
- Justificatifs SNCF officiels (SNCF Connect et TGV)
- Confirmations de réservation
- E-billets SNCF

### ⚠️ Non supportés :
- ❌ PDFs scannés non-OCR
- ❌ Images de billets
- ❌ PDFs protégés par mot de passe
- ❌ Billets d'autres compagnies (non-SNCF)

## 🚨 Dépannage

### Erreur : "Aucun fichier 'voyageurs_sncf_*.xlsx' généré"

**Causes possibles :**

1. **Pas de sous-dossiers** dans `./billets/`
   ```
   Solution : Créer au moins un dossier billets-train-XXX
   ```

2. **Mauvais nommage des dossiers**
   ```
   ❌ billets-train1        → Manque un tiret
   ✅ billets-train-WE1     → Correct
   ```

3. **Pas de fichiers PDF** dans les sous-dossiers
   ```
   Solution : Ajouter au moins 1 fichier .pdf par dossier
   ```

4. **Mauvais emplacement**
   ```
   Le dossier ./billets/ doit être au même niveau que main.py
   ```

### Vérification rapide :

```bash
# Depuis le dossier contenant main.py
ls -la ./billets/

# Devrait afficher :
# billets-train-WE1/
# billets-train-WE2/
# etc.

# Vérifier le contenu d'un sous-dossier
ls -la ./billets/billets-train-WE1/

# Devrait afficher des fichiers .pdf
```

## 💡 Conseils

### Organiser plusieurs weekends :

```
./billets/
├── billets-train-2025-01/    ← Par date
├── billets-train-2025-02/
├── billets-train-Lyon/       ← Par destination
├── billets-train-Paris/
└── billets-train-Test/       ← Pour tester
```

### Tester avec un seul weekend :

```
./billets/
└── billets-train-Test/
    └── justificatif_test.pdf
```

Lancez le pipeline : il traitera uniquement ce dossier et créera tous les fichiers avec `_Test` comme suffixe.

### Ajouter des weekends progressivement :

Le pipeline est **dynamique**, vous pouvez :
1. Commencer avec 1 dossier
2. Tester le pipeline
3. Ajouter d'autres dossiers
4. Relancer le pipeline (il traitera tous les dossiers trouvés)

## ✅ Check-list avant de lancer

- [ ] Dossier `./billets/` existe
- [ ] Au moins 1 sous-dossier au format `billets-train-XXX`
- [ ] Au moins 1 fichier PDF par sous-dossier
- [ ] Les PDFs sont des justificatifs SNCF valides
- [ ] Le script `main.py` est au même niveau que `./billets/`
- [ ] Toutes les dépendances sont installées (`pip install -r requirements.txt`)