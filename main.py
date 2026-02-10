"""
Pipeline complet de traitement des billets SNCF

Étapes :
1. Extraction des références SNCF depuis les PDF (PdfParserTickets.py)
2. Récupération des informations de trajet (Extract_SNCF_Trips_v5.py)
3. Suppression des doublons (Duplicate_Manager_Excel.py)
4. Conversion des villes en coordonnées GPS (cities_to_GPS_cache_v2.py)
5. Ajout des vérifications (Verifications_Trajets_v1.py)
6. Calcul des distances et génération des rapports finaux (signal_batch_distances_V3.py)

Tous les fichiers intermédiaires sont conservés pour audit.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Imports des modules de traitement
from PdfParserTickets import iterate_through_folders
from Extract_SNCF_Trips_v5 import extract_sncf_trips
from Duplicate_Manager_Excel import supprimer_doublons_trajets
from cities_to_GPS_cache_v2 import excel_cities_to_gps
from Verifications_Trajets_v1 import ajouter_verifications_simple
from signal_batch_distances_V3 import process_excel  # CORRIGÉ : vraie fonction


def log_step(step_number, total_steps, description, status="EN COURS"):
    """Affiche une étape du processus avec horodatage"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"[{timestamp}] ÉTAPE {step_number}/{total_steps} - {status}")
    print(f"{description}")
    print(f"{separator}\n")


def verify_file_exists(filepath):
    """Vérifie qu'un fichier existe et retourne son chemin Path"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {filepath}")
    return path


def main():
    """Exécution du pipeline complet"""
    
    # Configuration
    WEs = []  # Sera rempli dynamiquement après l'étape 1
    input_dir = "./billets"
    total_steps = 6
    
    start_time = time.time()
    print("\n" + "=" * 70)
    print("DÉMARRAGE DU PIPELINE DE TRAITEMENT DES BILLETS SNCF")
    print("=" * 70)
    print(f"Répertoire d'entrée : {input_dir}")
    print("Weekends à traiter : détection automatique...\n")
    
    try:
        # ===================================================================
        # ÉTAPE 1 : Extraction des références SNCF depuis les PDF
        # ===================================================================
        log_step(1, total_steps, "Extraction des références SNCF depuis les PDF")
        
        iterate_through_folders(input_dir)
        
        # Découvrir quels fichiers ont été créés
        # (le nom dépend des sous-dossiers dans ./billets/)
        generated_files = list(Path('.').glob('voyageurs_sncf_*.xlsx'))
        
        if not generated_files:
            raise FileNotFoundError(
                f"Aucun fichier 'voyageurs_sncf_*.xlsx' généré. "
                f"Vérifiez que le dossier '{input_dir}' contient des sous-dossiers "
                f"au format 'billets-WE-XXX' avec des PDF."
            )
        
        # Extraire les identifiants WE des fichiers générés
        WEs_found = []
        for file in generated_files:
            # Extraire 'WE1' depuis 'voyageurs_sncf_WE1.xlsx'
            we_id = file.stem.replace('voyageurs_sncf_', '')
            WEs_found.append(we_id)
            print(f"✓ Fichier créé : {file.name}")
        
        # Mettre à jour la liste WEs avec ce qui a vraiment été trouvé
        WEs = sorted(WEs_found)
        print(f"\nWeekends détectés : {', '.join(WEs)}")
        
        log_step(1, total_steps, "Extraction des références SNCF depuis les PDF", "TERMINÉE")
        
        
        # ===================================================================
        # ÉTAPE 2 : Extraction des informations de trajet SNCF
        # ===================================================================
        log_step(2, total_steps, "Récupération des informations de trajet depuis l'API SNCF")
        
        for we in WEs:
            input_file = f'voyageurs_sncf_{we}.xlsx'
            output_file = f'trajets_{we}_raw.xlsx'
            
            print(f"\nTraitement de {input_file}...")
            extract_sncf_trips(
                input_file=input_file,
                output_file=output_file,
                supprimer_doublons_flag=False  # On gère les doublons à l'étape suivante
            )
            
            # Vérification du fichier de sortie
            verify_file_exists(output_file)
            print(f"✓ Fichier créé : {output_file}")
        
        log_step(2, total_steps, "Récupération des informations de trajet", "TERMINÉE")
        
        
        # ===================================================================
        # ÉTAPE 3 : Suppression des doublons
        # ===================================================================
        log_step(3, total_steps, "Suppression des doublons entre références")
        
        for we in WEs:
            input_file = f'trajets_{we}_raw.xlsx'
            output_file = f'trajets_{we}_deduplicated.xlsx'
            
            print(f"\nTraitement de {input_file}...")
            supprimer_doublons_trajets(
                fichier_entree=input_file,
                fichier_sortie=output_file
            )
            
            # Vérification du fichier de sortie
            verify_file_exists(output_file)
            print(f"✓ Fichier créé : {output_file}")
        
        log_step(3, total_steps, "Suppression des doublons", "TERMINÉE")
        
        
        # ===================================================================
        # ÉTAPE 4 : Conversion des villes en coordonnées GPS
        # ===================================================================
        log_step(4, total_steps, "Conversion des noms de villes en coordonnées GPS")
        
        for we in WEs:
            input_file = f'trajets_{we}_deduplicated.xlsx'
            output_file = f'trajets_{we}_with_gps.xlsx'
            
            print(f"\nTraitement de {input_file}...")
            excel_cities_to_gps(
                input_file=input_file,
                output_file=output_file,
                cache_file="geocoding_cache.xlsx",
                city_columns=['Depart', 'Destination']
            )
            
            # Vérification du fichier de sortie
            verify_file_exists(output_file)
            print(f"✓ Fichier créé : {output_file}")
        
        log_step(4, total_steps, "Conversion GPS", "TERMINÉE")
        
        
        # ===================================================================
        # ÉTAPE 5 : Ajout des vérifications
        # ===================================================================
        log_step(5, total_steps, "Ajout des vérifications de cohérence des trajets")
        
        for we in WEs:
            input_file = f'trajets_{we}_with_gps.xlsx'
            output_file = f'trajets_{we}_verified.xlsx'
            
            print(f"\nTraitement de {input_file}...")
            ajouter_verifications_simple(
                fichier_entree=input_file,
                fichier_sortie=output_file
            )
            
            # Vérification du fichier de sortie
            verify_file_exists(output_file)
            print(f"✓ Fichier créé : {output_file}")
        
        log_step(5, total_steps, "Ajout des vérifications", "TERMINÉE")
        
        
        # ===================================================================
        # ÉTAPE 6 : Calcul des distances et génération des rapports finaux
        # ===================================================================
        log_step(6, total_steps, "Calcul des distances et génération des rapports finaux")
        
        for we in WEs:
            input_file = f'trajets_{we}_verified.xlsx'
            output_file = f'rapport_final_{we}.xlsx'
            
            print(f"\nTraitement de {input_file}...")
            process_excel(
                input_file=input_file,
                output_file=output_file,
                cache_file="trip_cache.json"
            )
            
            # Vérification du fichier de sortie
            verify_file_exists(output_file)
            print(f"✓ Fichier créé : {output_file}")
        
        log_step(6, total_steps, "Calcul des distances et génération des rapports", "TERMINÉE")
        
        
        # ===================================================================
        # RÉCAPITULATIF FINAL
        # ===================================================================
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        
        print("\n" + "=" * 70)
        print("PIPELINE TERMINÉ AVEC SUCCÈS")
        print("=" * 70)
        print(f"Durée totale : {minutes} min {seconds} s\n")
        
        print("FICHIERS FINAUX GÉNÉRÉS :")
        for we in WEs:
            final_file = f'rapport_final_{we}.xlsx'
            print(f"  ✓ {final_file}")
        
        print("\nFICHIERS INTERMÉDIAIRES CONSERVÉS (pour audit) :")
        for we in WEs:
            print(f"\n  Weekend {we} :")
            print(f"    • voyageurs_sncf_{we}.xlsx (Étape 1 - Extraction PDF)")
            print(f"    • trajets_{we}_raw.xlsx (Étape 2 - Extraction API)")
            print(f"    • trajets_{we}_deduplicated.xlsx (Étape 3 - Déduplication)")
            print(f"    • trajets_{we}_with_gps.xlsx (Étape 4 - Géocodage)")
            print(f"    • trajets_{we}_verified.xlsx (Étape 5 - Vérifications)")
        
        print("\nAUTRES FICHIERS :")
        print("  • geocoding_cache.xlsx (Cache des coordonnées GPS)")
        print("  • trip_cache.json (Cache des trajets et distances)")
        
        print("\n" + "=" * 70 + "\n")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())