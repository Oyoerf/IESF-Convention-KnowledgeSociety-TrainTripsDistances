"""
Pipeline complet de traitement des billets SNCF

Étapes :
1. Extraction des références SNCF depuis les PDF (PdfParserTickets.py)
2. Récupération des informations de trajet (Extract_SNCF_Trips_v6.py)
3. Suppression des doublons (Duplicate_Manager_Excel.py)
4. Conversion des villes en coordonnées GPS (cities_to_GPS_cache_v2.py)
5. Ajout des vérifications (Verifications_Trajets_v1.py)
6. Calcul des distances et génération des rapports finaux (signal_batch_distances_V3.py)

Tous les fichiers intermédiaires sont conservés pour audit.
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Imports des modules de traitement
from TicketsParser import iterate_through_folders
from ExtractTrainTrips import extract_sncf_trips
from DuplicateManagerExcel import supprimer_doublons_trajets
from CitiesToGPS import excel_cities_to_gps
from TripsCheck import ajouter_verifications_simple
from DistancesComputationBatch import process_excel


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


def wait_for_user_validation():
    """Attend la validation de l'utilisateur avant de continuer"""
    print("\n" + "=" * 70)
    print("⏸️  PAUSE - Validation requise")
    print("=" * 70)
    response = input("Appuyez sur ENTRÉE pour continuer (ou 'q' pour quitter) : ").strip().lower()
    if response == 'q':
        print("\n❌ Pipeline arrêté par l'utilisateur")
        sys.exit(0)
    print("=" * 70 + "\n")


def discover_weekends():
    """Découvre automatiquement les weekends à partir des fichiers générés"""
    generated_files = list(Path('.').glob('voyageurs_sncf_*.xlsx'))
    
    if not generated_files:
        return []
    
    WEs_found = []
    for file in generated_files:
        we_id = file.stem.replace('voyageurs_sncf_', '')
        WEs_found.append(we_id)
    
    return sorted(WEs_found)


def step1_extract_references(input_dir, interactive=False):
    """
    ÉTAPE 1 : Extraction des références SNCF depuis les PDF
    
    Returns:
        list: Liste des identifiants de weekends détectés
    """
    log_step(1, 6, "Extraction des références SNCF depuis les PDF")
    
    iterate_through_folders(input_dir)
    
    # Découvrir quels fichiers ont été créés
    generated_files = list(Path('.').glob('voyageurs_sncf_*.xlsx'))
    
    if not generated_files:
        raise FileNotFoundError(
            f"Aucun fichier 'voyageurs_sncf_*.xlsx' généré. "
            f"Vérifiez que le dossier '{input_dir}' contient des sous-dossiers "
            f"au format 'billets-WE-XXX' avec des PDF."
        )
    
    # Extraire les identifiants WE
    WEs_found = []
    for file in generated_files:
        we_id = file.stem.replace('voyageurs_sncf_', '')
        WEs_found.append(we_id)
        print(f"✓ Fichier créé : {file.name}")
    
    WEs = sorted(WEs_found)
    print(f"\nWeekends détectés : {', '.join(WEs)}")
    
    log_step(1, 6, "Extraction des références SNCF depuis les PDF", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()
    
    return WEs


def step2_extract_trips(WEs, interactive=False):
    """ÉTAPE 2 : Extraction des informations de trajet SNCF"""
    log_step(2, 6, "Récupération des informations de trajet depuis l'API SNCF")
    
    for we in WEs:
        input_file = f'voyageurs_sncf_{we}.xlsx'
        output_file = f'trajets_{we}_raw.xlsx'
        
        print(f"\nTraitement de {input_file}...")
        extract_sncf_trips(
            input_file=input_file,
            output_file=output_file,
            supprimer_doublons_flag=False
        )
        
        verify_file_exists(output_file)
        print(f"✓ Fichier créé : {output_file}")
    
    log_step(2, 6, "Récupération des informations de trajet", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()


def step3_remove_duplicates(WEs, interactive=False):
    """ÉTAPE 3 : Suppression des doublons"""
    log_step(3, 6, "Suppression des doublons entre références")
    
    for we in WEs:
        input_file = f'trajets_{we}_raw.xlsx'
        output_file = f'trajets_{we}_deduplicated.xlsx'
        
        print(f"\nTraitement de {input_file}...")
        supprimer_doublons_trajets(
            fichier_entree=input_file,
            fichier_sortie=output_file
        )
        
        verify_file_exists(output_file)
        print(f"✓ Fichier créé : {output_file}")
    
    log_step(3, 6, "Suppression des doublons", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()


def step4_geocoding(WEs, interactive=False):
    """ÉTAPE 4 : Conversion des villes en coordonnées GPS"""
    log_step(4, 6, "Conversion des noms de villes en coordonnées GPS")
    
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
        
        verify_file_exists(output_file)
        print(f"✓ Fichier créé : {output_file}")
    
    log_step(4, 6, "Conversion GPS", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()


def step5_add_verifications(WEs, interactive=False):
    """ÉTAPE 5 : Ajout des vérifications"""
    log_step(5, 6, "Ajout des vérifications de cohérence des trajets")
    
    for we in WEs:
        input_file = f'trajets_{we}_with_gps.xlsx'
        output_file = f'trajets_{we}_verified.xlsx'
        
        print(f"\nTraitement de {input_file}...")
        ajouter_verifications_simple(
            fichier_entree=input_file,
            fichier_sortie=output_file
        )
        
        verify_file_exists(output_file)
        print(f"✓ Fichier créé : {output_file}")
    
    log_step(5, 6, "Ajout des vérifications", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()


def step6_calculate_distances(WEs, interactive=False):
    """ÉTAPE 6 : Calcul des distances et génération des rapports finaux"""
    log_step(6, 6, "Calcul des distances et génération des rapports finaux")
    
    for we in WEs:
        input_file = f'trajets_{we}_verified.xlsx'
        output_file = f'rapport_final_{we}.xlsx'
        
        print(f"\nTraitement de {input_file}...")
        process_excel(
            input_file=input_file,
            output_file=output_file,
            cache_file="trip_cache.json"
        )
        
        verify_file_exists(output_file)
        print(f"✓ Fichier créé : {output_file}")
    
    log_step(6, 6, "Calcul des distances et génération des rapports", "TERMINÉE")
    
    if interactive:
        wait_for_user_validation()


def print_summary(WEs, start_time):
    """Affiche le récapitulatif final"""
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


def main():
    """Point d'entrée principal avec gestion des arguments"""
    
    # Configuration du parser d'arguments
    parser = argparse.ArgumentParser(
        description="Pipeline de traitement des billets SNCF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  
  # Exécuter le pipeline complet
  python main.py
  
  # Exécuter uniquement l'extraction des PDF (étape 1)
  python main.py --extract-only
  
  # Partir d'un Excel existant et faire toute la suite
  python main.py --from-excel
  
  # S'arrêter après le géocodage (étapes 1-4)
  python main.py --stop-after-geocoding
  
  # Mode interactif : pause après chaque étape
  python main.py --interactive
  
  # Combiner plusieurs options
  python main.py --from-excel --stop-after-geocoding --interactive
        """
    )
    
    # Options de parcours du pipeline
    parser.add_argument(
        '--extract-only',
        action='store_true',
        help="Exécuter uniquement l'étape 1 (extraction des références depuis les PDF)"
    )
    
    parser.add_argument(
        '--from-excel',
        action='store_true',
        help="Partir des fichiers voyageurs_sncf_*.xlsx existants (sauter l'étape 1)"
    )
    
    parser.add_argument(
        '--stop-after-geocoding',
        action='store_true',
        help="S'arrêter après l'étape 4 (géocodage GPS)"
    )
    
    parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help="Mode interactif : demander validation après chaque étape"
    )
    
    # Options de configuration
    parser.add_argument(
        '--input-dir',
        type=str,
        default='./billets',
        help="Répertoire contenant les billets PDF (défaut: ./billets)"
    )
    
    args = parser.parse_args()
    
    # Configuration
    input_dir = args.input_dir
    interactive = args.interactive
    
    start_time = time.time()
    print("\n" + "=" * 70)
    print("DÉMARRAGE DU PIPELINE DE TRAITEMENT DES BILLETS SNCF")
    print("=" * 70)
    
    # Afficher le mode d'exécution
    if args.extract_only:
        print("Mode : Extraction uniquement (étape 1)")
    elif args.from_excel:
        if args.stop_after_geocoding:
            print("Mode : Depuis Excel, s'arrêter après géocodage (étapes 2-4)")
        else:
            print("Mode : Depuis Excel jusqu'à la fin (étapes 2-6)")
    elif args.stop_after_geocoding:
        print("Mode : Pipeline complet jusqu'au géocodage (étapes 1-4)")
    else:
        print("Mode : Pipeline complet (étapes 1-6)")
    
    if interactive:
        print("⏸️  Mode interactif activé : pause après chaque étape")
    
    print(f"Répertoire d'entrée : {input_dir}\n")
    
    try:
        WEs = []
        
        # ===================================================================
        # ÉTAPE 1 : Extraction des références (sauf si --from-excel)
        # ===================================================================
        if not args.from_excel:
            WEs = step1_extract_references(input_dir, interactive)
            
            if args.extract_only:
                print("\n✅ Extraction terminée (--extract-only)")
                return 0
        else:
            # Découvrir les weekends depuis les fichiers existants
            print("⏭️  Étape 1 ignorée (--from-excel)")
            WEs = discover_weekends()
            
            if not WEs:
                raise FileNotFoundError(
                    "Aucun fichier 'voyageurs_sncf_*.xlsx' trouvé. "
                    "Lancez d'abord l'extraction des PDF ou retirez --from-excel."
                )
            
            print(f"Weekends détectés : {', '.join(WEs)}\n")
        
        # ===================================================================
        # ÉTAPE 2 : Extraction des trajets
        # ===================================================================
        step2_extract_trips(WEs, interactive)
        
        # ===================================================================
        # ÉTAPE 3 : Suppression des doublons
        # ===================================================================
        step3_remove_duplicates(WEs, interactive)
        
        # ===================================================================
        # ÉTAPE 4 : Géocodage
        # ===================================================================
        step4_geocoding(WEs, interactive)
        
        if args.stop_after_geocoding:
            print("\n✅ Pipeline arrêté après le géocodage (--stop-after-geocoding)")
            print("\nFichiers générés :")
            for we in WEs:
                print(f"  ✓ trajets_{we}_with_gps.xlsx")
            return 0
        
        # ===================================================================
        # ÉTAPE 5 : Vérifications
        # ===================================================================
        step5_add_verifications(WEs, interactive)
        
        # ===================================================================
        # ÉTAPE 6 : Calcul des distances
        # ===================================================================
        step6_calculate_distances(WEs, interactive)
        
        # ===================================================================
        # RÉCAPITULATIF FINAL
        # ===================================================================
        print_summary(WEs, start_time)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr)
        return 1
    
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline interrompu par l'utilisateur (Ctrl+C)")
        return 130
    
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE : {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())