import time
import requests
import pandas as pd
import pdfplumber
import re
from io import BytesIO

def recuperer_uuid_et_infos(reference, nom):
    """
    Récupère les informations de base depuis l'API orders.
    Génère un UUID aléatoire pour chaque requête.
    Retourne (uuid, prenom, nom_famille) ou (None, None, None) en cas d'erreur.
    """
    import uuid as uuid_lib
    
    url = "https://www.sncf-voyageurs.com/api/pao/orders/"
    
    uuid_session = str(uuid_lib.uuid4())
    
    params = {
        'reference': reference,
        'passengerName': nom,
        'uuid': uuid_session
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Referer': 'https://www.sncf-voyageurs.com/',
        'Origin': 'https://www.sncf-voyageurs.com'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'passengersData' in data and len(data['passengersData']) > 0:
                passenger = data['passengersData'][0]
                prenom = passenger.get('passengerFirstName', '')
                nom_famille = passenger.get('passengerLastName', nom)
            else:
                prenom = ''
                nom_famille = nom
            
            print(f"    Infos récupérées - Prénom: {prenom}, Nom: {nom_famille}")
            return uuid_session, prenom, nom_famille
        else:
            print(f"    Erreur récupération infos pour {nom} ({reference}): {response.status_code}")
            return None, None, None
            
    except Exception as e:
        print(f"    Exception récupération infos pour {nom} ({reference}): {e}")
        return None, None, None


def telecharger_justificatif_pdf(reference, name, uuid):
    """
    Télécharge le PDF du justificatif de voyage depuis l'API SNCF.
    
    Retourne le contenu du PDF en bytes ou None en cas d'erreur.
    """
    url = "https://www.sncf-voyageurs.com/api/pao/pdf/"
    params = {'uuid': uuid}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/pdf',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Referer': 'https://www.sncf-voyageurs.com/',
        'Origin': 'https://www.sncf-voyageurs.com'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('application/pdf'):
            return response.content
        else:
            print(f"    Erreur téléchargement PDF pour {name} ({reference}): {response.status_code}")
            return None
    except Exception as e:
        print(f"    Exception lors du téléchargement pour {name} ({reference}): {e}")
        return None


def extraire_trajets_depuis_pdf(pdf_content, nom, prenom):
    """
    Extrait TOUS les trajets depuis le contenu PDF du justificatif de voyage.
    Gère 3 formats de justificatifs SNCF différents et PDFs multi-trajets.
    
    Retourne une liste de dictionnaires avec les informations de trajet.
    """
    trajets = []
    
    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            texte = ""
            for page in pdf.pages:
                texte += page.extract_text() + "\n"
            
            # FORMAT 1: "ALLER le DD-MM-YYYY de GARE1 à GARE2 Seconde classe"
            # Peut contenir plusieurs passagers entre les gares et "classe"
            pattern1 = re.findall(
                r'(?:ALLER|RETOUR)\s+le\s+\d{2}[/-]\d{2}[/-]\d{4}\s+de\s+([A-ZÀ-Ü\s\-\']+?)\s+à\s+([A-ZÀ-Ü\s\-\']+?)\s+(?:Seconde|Première)\s+classe',
                texte,
                re.IGNORECASE
            )
            
            for depart, destination in pattern1:
                trajets.append({
                    'Departure': depart.strip(),
                    'Destination': destination.strip(),
                    'TrainType': 'TER'
                })
            
            # FORMAT 2: Tableau avec gares et horaires + ligne "TGV INOUI XXXX"
            # Découper par "Départ / Arrivée" pour gérer les PDFs multi-trajets
            if not pattern1:
                sections = re.split(r'Départ\s*/\s*Arrivée', texte)
                
                for section in sections[1:]:  # Ignorer partie avant le premier "Départ / Arrivée"
                    gares = re.findall(
                        r'^([A-ZÀ-Ü\s\-\']{3,})\s+\d{2}/\d{2}\s+à\s+\d{2}h\d{2}',
                        section,
                        re.MULTILINE
                    )
                    
                    train_match = re.search(r'(TGV INOUI|TER|INTERCITES|OUIGO)\s+\d+', section)
                    
                    if len(gares) >= 2:
                        type_train = train_match.group(1) if train_match else 'TGV'
                        trajets.append({
                            'Departure': gares[0].strip(),
                            'Destination': gares[1].strip(),
                            'TrainType': type_train
                        })
            
            # FORMAT 3: "De GARE1 pour X adulte(s)" puis "à GARE2"
            if not pattern1 and not trajets:
                pattern3 = re.search(
                    r'De\s+([A-ZÀ-Ü\s\-\']+?)\s+pour\s+\d+\s+adulte.*?à\s+([A-ZÀ-Ü\s\-\']+)',
                    texte,
                    re.IGNORECASE | re.DOTALL
                )
                
                if pattern3:
                    trajets.append({
                        'Departure': pattern3.group(1).strip(),
                        'Destination': pattern3.group(2).strip(),
                        'TrainType': 'TER'
                    })
            
    except Exception as e:
        print(f"    Erreur extraction PDF: {e}")
    
    return trajets


def getTransportInfo(reference, nom):
    """
    Récupère les informations de transport depuis l'API orders JSON.
    Les données JSON sont complètes et fiables (pas besoin de PDF).
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
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"    Erreur API pour {nom} ({reference}): {response.status_code}")
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
            
            print(f"    {len(travels)} trajet(s) extrait(s)")
        else:
            print(f"    Aucune donnée passager trouvée")
            travels.append({
                'Name': 'Not found',
                'LastName': nom,
                'Departure': 'Not found',
                'Destination': 'Not found',
                'TrainType': 'Not found',
            })
        
        return travels
        
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
    Extrait les trajets SNCF depuis l'API JSON et supprime les doublons.
    
    Paramètres:
    - input_file: Fichier Excel avec colonnes 'Nom' et 'Ref'
    - output_file: Fichier Excel de sortie (défaut: input_file_with_trips.xlsx)
    - supprimer_doublons_flag: Si True, supprime les doublons entre références
    """
    
    if output_file is None:
        base_name = input_file.rsplit('.', 1)[0]
        output_file = f"{base_name}_with_trips_v5.xlsx"
    
    print(f"Lecture du fichier Excel: {input_file}")
    df = pd.read_excel(input_file)
    
    colonnes = df.columns.str.lower().tolist()
    
    if 'nom' not in colonnes or 'ref' not in colonnes:
        raise ValueError(f"Le fichier Excel doit contenir les colonnes 'Nom' et 'Ref'. Colonnes trouvées: {list(df.columns)}")
    
    df.columns = df.columns.str.lower()
    
    result = {
        'Nom': [],
        'Prenom': [],
        'Reference': [],
        'Depart': [],
        'Destination': [],
        'Type de train': []
    }
    
    print(f"Traitement de {len(df)} références...")
    print(f"Source: API SNCF Voyageurs (JSON)\n")
    
    for i, row in df.iterrows():
        nom = row['nom']
        reference = row['ref']
        
        print(f"  [{i+1}/{len(df)}] {nom} - Ref: {reference}")
        
        trajets = getTransportInfo(reference=reference, nom=nom)
        
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
    extract_sncf_trips('voyageurs_WE1_valid.xlsx')