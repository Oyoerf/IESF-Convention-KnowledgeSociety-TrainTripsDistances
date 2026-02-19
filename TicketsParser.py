#!/usr/bin/env python3
"""
Extracteur batch de justificatifs SNCF
Extrait uniquement la référence et le nom complet du voyageur 1.
"""

import pandas as pd
import pdfplumber
import re
from pathlib import Path
import sys


def extract_references(text):
    """
    Extrait toutes les références du dossier depuis le texte du PDF.
    
    Args:
        text: Texte complet du PDF
    
    Returns:
        list: Liste de toutes les références trouvées
    """
    # Pattern pour "Réf: XXXXXX" ou "Réf : XXXXXX"
    pattern = r"Réf\s*:\s*([A-Z0-9]+)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    return [ref.strip() for ref in matches] if matches else []


def extract_travelers(text):
    """
    Extrait le nom complet de tous les voyageurs 1 depuis le texte du PDF.
    IMPORTANT: Retourne le nom COMPLET tel quel (PRENOM NOM), sans séparation.
    
    Args:
        text: Texte complet du PDF
    
    Returns:
        list: Liste de noms complets pour chaque voyageur 1 trouvé
    """
    # Pattern pour "Voyageur 1 : PRENOM NOM"
    pattern = r"Voyageur\s+1\s*:\s*([A-ZÀ-ÿ\s-]+?)(?:\s*-\s*Carte|\n|$)"
    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
    
    travelers = []
    
    for match in matches:
        full_name = match.group(1).strip()
        # Nettoyer le nom (enlever les informations de carte)
        full_name = re.sub(r'\s*-\s*Carte.*$', '', full_name, flags=re.IGNORECASE)
        full_name = full_name.strip()
        
        if full_name:
            travelers.append(full_name)
    
    return travelers if travelers else []


def extract_pdf_data(pdf_path):
    """
    Extrait les données d'un justificatif SNCF PDF.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
    
    Returns:
        list: Liste de dictionnaires avec les informations (une entrée par référence)
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extraire tout le texte
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Extraire les informations
            references = extract_references(full_text)
            travelers = extract_travelers(full_text)
            
            if not references or not travelers:
                print(f"⚠️  Avertissement : Données incomplètes dans {pdf_path.name}")
                print(f"    Références: {references}, Voyageurs: {len(travelers) if travelers else 0}")
                return []
            
            # Si le nombre de références et de voyageurs ne correspond pas, on prend le minimum
            min_count = min(len(references), len(travelers))
            
            results = []
            for i in range(min_count):
                results.append({
                    'NomComplet': travelers[i],
                    'Ref': references[i]
                })
            
            return results
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement de {pdf_path.name}: {e}")
        return []


def process_batch(input_dir, output_file):
    """
    Traite tous les PDF d'un répertoire et génère un fichier Excel.
    
    Args:
        input_dir: Répertoire contenant les PDF
        output_file: Chemin du fichier Excel de sortie
    
    Returns:
        pd.DataFrame: DataFrame avec tous les voyageurs extraits
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Le répertoire '{input_dir}' n'existe pas")
    
    # Trouver tous les fichiers PDF
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"Aucun fichier PDF trouvé dans '{input_dir}'")
        return None
    
    print(f"Trouvé {len(pdf_files)} fichier(s) PDF à traiter\n")
    
    all_data = []
    
    # Traiter chaque PDF
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Traitement de {pdf_file.name}...", end=" ")
        
        data_list = extract_pdf_data(pdf_file)
        
        if data_list:
            all_data.extend(data_list)
            print(f"✓ {len(data_list)} entrée(s) extraite(s)")
        else:
            print("✗ Aucune donnée extraite")
    
    # Créer le DataFrame
    if not all_data:
        print("\n❌ Aucune donnée n'a pu être extraite des PDF")
        return None
    
    df = pd.DataFrame(all_data)
    
    # Définir l'ordre des colonnes : NomComplet, Ref
    df = df[['NomComplet', 'Ref']]
    
    # Sauvegarder en Excel
    df.to_excel(output_file, index=False)
    
    print(f"\n{'='*60}")
    print(f"RÉSUMÉ")
    print(f"{'='*60}")
    print(f"Total de fichiers traités  : {len(pdf_files)}")
    print(f"Total d'entrées extraites  : {len(all_data)}")
    print(f"Fichier de sortie          : {output_file}")
    print(f"{'='*60}")
    
    return df

def iterate_through_folders(root_dir):
    """
    Itère à travers tous les sous-répertoires pour traiter les PDF.
    
    Args:
        root_dir: Répertoire racine contenant des sous-répertoires avec des PDF
    """
    root_path = Path(root_dir)
    
    if not root_path.exists():
        raise FileNotFoundError(f"Le répertoire '{root_dir}' n'existe pas")
    
    # Itérer à travers chaque sous-répertoire
    for subdir in root_path.iterdir():
        if subdir.is_dir():
            print(f"\nTraitement du répertoire : {subdir.name}")
            name = subdir.name.split('-')[2]
            output_file = f'voyageurs_sncf_{name}.xlsx'
            process_batch(subdir, output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sncf_batch_extractor.py <répertoire_pdf> [fichier_sortie.xlsx]")
        print("\nExemples:")
        print("  python3 sncf_batch_extractor.py ./justificatifs")
        print("  python3 sncf_batch_extractor.py ./justificatifs voyageurs.xlsx")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "voyageurs_sncf.xlsx"
    
    try:
        df = process_batch(input_dir, output_file)
        if df is not None:
            print("\n✅ Traitement terminé avec succès !")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        sys.exit(1)