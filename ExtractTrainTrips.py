import time
import requests
import pandas as pd
import sys
from pathlib import Path


def getTransportInfo_with_incremental_name(reference, nom_complet):
    """
    Essaie plusieurs variantes du nom de famille jusqu'à trouver la bonne.
    Approche incrémentale : commence par le dernier mot, puis ajoute progressivement.
    
    IMPORTANT: Cette fonction NE retourne PAS le nom/prénom décomposé.
    Elle utilise juste cette logique en interne pour trouver les trajets.
    
    Args:
        reference: Référence SNCF
        nom_complet: Nom complet tel qu'extrait du PDF (ex: "Jean Claude MARTIN DUBOIS")
    
    Returns:
        list: Liste des trajets trouvés (ou "Not found" si échec total)
    """
    if not nom_complet or nom_complet.strip() == '':
        return [{
            'Name': 'Error',
            'LastName': '',
            'Departure': 'Error',
            'Destination': 'Error',
            'TrainType': 'Error',
        }]
    
    # Séparer le nom complet en mots
    parts = nom_complet.strip().split()
    
    if len(parts) == 0:
        return [{
            'Name': 'Error',
            'LastName': nom_complet,
            'Departure': 'Error',
            'Destination': 'Error',
            'TrainType': 'Error',
        }]
    
    # Générer les variantes (du plus spécifique au plus général)
    # Ex pour ['Jean', 'Claude', 'MARTIN', 'DUBOIS']:
    # 1. 'DUBOIS'
    # 2. 'MARTIN DUBOIS'
    # 3. 'CLAUDE MARTIN DUBOIS'
    # 4. 'JEAN CLAUDE MARTIN DUBOIS'
    
    attempts = []
    for i in range(1, len(parts) + 1):
        nom_test = ' '.join(parts[-i:])
        attempts.append(nom_test)
    
    print(f"    Tentatives pour '{nom_complet}' (Ref: {reference}):", end="")
    
    for attempt_num, nom_test in enumerate(attempts, 1):
        travels = getTransportInfo(reference, nom_test)
        
        # Vérifier si l'appel a réussi
        if travels and len(travels) > 0:
            first_travel = travels[0]
            
            # Si on a trouvé des données valides (pas "Not found" ou "Error")
            if (first_travel['Name'] not in ['Not found', 'Error', ''] and 
                first_travel['Departure'] not in ['Not found', 'Error', 'Unknown']):
                
                print(f" ✓ [{attempt_num}/{len(attempts)}]")
                return travels
        
        # Petit délai entre les tentatives pour ne pas surcharger l'API
        if attempt_num < len(attempts):
            time.sleep(0.3)
    
    # Aucune tentative n'a fonctionné
    print(f" ✗ Échec après {len(attempts)} tentatives")
    
    return [{
        'Name': 'Not found',
        'LastName': 'Not found',
        'Departure': 'Not found',
        'Destination': 'Not found',
        'TrainType': 'Not found',
    }]


def getTransportInfo(reference, nom):
    """
    Récupère les informations de transport depuis l'API orders JSON.
    
    Args:
        reference: Référence SNCF
        nom: Nom de famille à tester
    
    Returns:
        list: Liste des trajets ou liste avec "Not found" si échec
    """
    url = "https://www.sncf-voyageurs.com/api/pao/orders/"
    
    import uuid as uuid_lib
    uuid_req = str(uuid_lib.uuid4())
    
    params = {
        'reference': reference,
        'passengerName': nom,
        'uuid': uuid_req
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Referer': 'https://www.sncf-voyageurs.com/',
        'Origin': 'https://www.sncf-voyageurs.com'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return [{
                'Name': 'Not found',
                'LastName': nom,
                'Departure': 'Not found',
                'Destination': 'Not found',
                'TrainType': 'Not found',
            }]
        
        data = response.json()
        travels = []
        
        if 'passengersData' in data and len(data['passengersData']) > 0:
            for passenger in data['passengersData']:
                prenom = passenger.get('passengerFirstName', '')
                nom_famille = passenger.get('passengerLastName', nom)
                
                # Trajets aller
                if 'travels' in passenger:
                    for trip in passenger['travels']:
                        travels.append({
                            'Name': prenom,
                            'LastName': nom_famille,
                            'Departure': trip.get('origin', 'Unknown'),
                            'Destination': trip.get('destination', 'Unknown'),
                            'TrainType': trip.get('trainType', 'Unknown')
                        })
                
                # Trajets retour
                if 'travelsBack' in passenger:
                    for trip in passenger['travelsBack']:
                        travels.append({
                            'Name': prenom,
                            'LastName': nom_famille,
                            'Departure': trip.get('origin', 'Unknown'),
                            'Destination': trip.get('destination', 'Unknown'),
                            'TrainType': trip.get('trainType', 'Unknown')
                        })
            
            return travels if travels else [{
                'Name': 'Not found',
                'LastName': nom,
                'Departure': 'Not found',
                'Destination': 'Not found',
                'TrainType': 'Not found',
            }]
        else:
            return [{
                'Name': 'Not found',
                'LastName': nom,
                'Departure': 'Not found',
                'Destination': 'Not found',
                'TrainType': 'Not found',
            }]
        
    except Exception as e:
        print(f"    Exception pour {nom} ({reference}): {e}")
        return [{
            'Name': 'Error',
            'LastName': nom,
            'Departure': 'Error',
            'Destination': 'Error',
            'TrainType': 'Error',
        }]


def supprimer_doublons(df):
    """
    Supprime les doublons de trajets entre références différentes.
    Conserve tous les trajets au sein d'une même référence (aller-retour),
    mais supprime les trajets des autres références s'ils existent déjà.
    """
    nb_lignes_avant = len(df)
    
    lignes_a_garder = []
    trajets_vus_par_personne = {}
    
    for idx, row in df.iterrows():
        personne = (row['Nom'], row['Prenom'])
        trajet = (row['Depart'], row['Destination'])
        reference = row['Reference']
        
        if personne not in trajets_vus_par_personne:
            trajets_vus_par_personne[personne] = {}
        
        if trajet not in trajets_vus_par_personne[personne]:
            trajets_vus_par_personne[personne][trajet] = reference
            lignes_a_garder.append(idx)
        elif trajets_vus_par_personne[personne][trajet] == reference:
            lignes_a_garder.append(idx)
    
    df_unique = df.loc[lignes_a_garder]
    nb_doublons_supprimes = nb_lignes_avant - len(df_unique)
    
    print(f"  - Doublons supprimés : {nb_doublons_supprimes}")
    
    return df_unique


def extract_sncf_trips(input_file, output_file=None, supprimer_doublons_flag=True):
    """
    Extrait les trajets SNCF depuis l'API JSON avec détection intelligente des noms composés.
    
    LOGIQUE:
    - Fichier d'entrée : colonnes 'NomComplet' et 'Ref'
    - Détection automatique des noms composés en background (invisible pour l'utilisateur)
    - Fichier de sortie : colonnes standards avec Nom/Prenom tels que retournés par l'API
    
    Paramètres:
    - input_file: Fichier Excel avec colonnes 'NomComplet' et 'Ref'
    - output_file: Fichier Excel de sortie (défaut: input_file_with_trips.xlsx)
    - supprimer_doublons_flag: Si True, supprime les doublons entre références
    """
    
    if output_file is None:
        base_name = input_file.rsplit('.', 1)[0]
        # Retirer le suffixe _sncf si présent pour éviter les doublons
        if base_name.endswith('_sncf'):
            base_name = base_name[:-5]
        output_file = f"trajets_{base_name.split('_')[-1]}_raw.xlsx"
    
    print(f"Lecture du fichier Excel: {input_file}")
    df = pd.read_excel(input_file)
    
    # Vérifier les colonnes (accepter NomComplet ou les anciennes colonnes Nom/Prenom)
    colonnes = df.columns.str.lower().tolist()
    
    if 'nomcomplet' in colonnes and 'ref' in colonnes:
        # Nouveau format avec NomComplet
        df.columns = df.columns.str.lower()
        use_nomcomplet = True
    elif 'nom' in colonnes and 'ref' in colonnes:
        # Ancien format avec Nom séparé (rétrocompatibilité)
        df.columns = df.columns.str.lower()
        # Créer la colonne NomComplet
        if 'prenom' in colonnes:
            df['nomcomplet'] = df['prenom'] + ' ' + df['nom']
        else:
            df['nomcomplet'] = df['nom']
        use_nomcomplet = True
    else:
        raise ValueError(
            f"Le fichier Excel doit contenir soit 'NomComplet' et 'Ref', "
            f"soit 'Nom' et 'Ref'. Colonnes trouvées: {list(df.columns)}"
        )
    
    result = {
        'Nom': [],
        'Prenom': [],
        'Reference': [],
        'Depart': [],
        'Destination': [],
        'Type de train': []
    }
    
    print(f"Traitement de {len(df)} références...")
    print(f"Source: API SNCF Voyageurs (JSON) avec détection automatique des noms composés\n")
    
    for i, row in df.iterrows():
        nom_complet = row['nomcomplet']
        reference = row['ref']
        
        print(f"  [{i+1}/{len(df)}] '{nom_complet}' - Ref: {reference}")
        
        # Utiliser la fonction avec détection incrémentale
        # La logique de décomposition se fait en BACKGROUND
        trajets = getTransportInfo_with_incremental_name(reference, nom_complet)
        
        # Ajouter les trajets au résultat
        # On garde Nom et Prenom tels que retournés par l'API
        for trip in trajets:
            result['Nom'].append(trip['LastName'])
            result['Prenom'].append(trip['Name'])
            result['Reference'].append(reference)
            result['Depart'].append(trip['Departure'])
            result['Destination'].append(trip['Destination'])
            result['Type de train'].append(trip['TrainType'])
        
        time.sleep(0.5)
    
    df_result = pd.DataFrame(result)
    print(f"\nTrajets extraits: {len(df_result)}")
    
    if supprimer_doublons_flag:
        print("Suppression des doublons entre références...")
        df_result = supprimer_doublons(df_result)
        print(f"Trajets après dédoublonnage: {len(df_result)}")
    
    print(f"\nEnregistrement dans: {output_file}")
    df_result.to_excel(output_file, index=False)
    print("Terminé!")
    
    return df_result


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 Extract_SNCF_Trips_v7.py <fichier_voyageurs.xlsx>")
        print("\nExemple:")
        print("  python3 Extract_SNCF_Trips_v7.py voyageurs_sncf_WE1.xlsx")
        sys.exit(1)
    
    input_file = sys.argv[1]
    extract_sncf_trips(input_file)