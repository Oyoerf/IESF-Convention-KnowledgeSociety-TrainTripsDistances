import pandas as pd
import requests
import time
import sys
import hashlib
import json
from pathlib import Path


BASE_URL = "https://signal.eu.org/osm/eu/route/v1/train"


class TripCache:
    """Gère un cache persistant des trajets ferroviaires avec normalisation des coordonnées."""
    
    def __init__(self, cache_file="trip_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.stats = {'cache_hits': 0, 'api_calls': 0, 'failures': 0}
    
    @staticmethod
    def normalize_city_name(city_name):
        """
        Normalise le nom d'une ville pour le cache.
        - Convertit en majuscules
        - Supprime les tirets
        - Normalise les espaces multiples en un seul espace
        - Supprime les espaces en début et fin
        
        Args:
            city_name: Nom de la ville à normaliser
        
        Returns:
            str: Nom normalisé en majuscules sans tirets
        """
        if pd.isna(city_name):
            return None
        normalized = str(city_name).upper().strip()
        # Remplacer les tirets par des espaces
        normalized = normalized.replace('-', ' ')
        # Normaliser les espaces multiples en un seul espace
        normalized = ' '.join(normalized.split())
        # Ignorer "NOT FOUND"
        if normalized == 'NOT FOUND':
            return None
        return normalized
    
    def _load_cache(self):
        """Charge le cache depuis le fichier JSON s'il existe."""
        if Path(self.cache_file).exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                print(f"Cache chargé : {len(cache_data)} trajets trouvés dans '{self.cache_file}'")
                return cache_data
            except Exception as e:
                print(f"Avertissement : Impossible de charger le cache : {e}")
                return {}
        else:
            print(f"Aucun cache trouvé. Un nouveau sera créé : '{self.cache_file}'")
            return {}
    
    def _generate_key(self, origin, destination, via=None):
        """
        Génère une clé unique pour un trajet basée sur les noms de villes normalisés.
        
        Args:
            origin: Nom de la ville d'origine
            destination: Nom de la ville de destination
            via: Nom de la ville intermédiaire (optionnel)
        
        Returns:
            str: Clé MD5 du trajet
        """
        origin_norm = self.normalize_city_name(origin)
        dest_norm = self.normalize_city_name(destination)
        
        if origin_norm is None or dest_norm is None:
            return None
        
        key_str = f"{origin_norm}|{dest_norm}"
        
        if via is not None:
            via_norm = self.normalize_city_name(via)
            if via_norm:
                key_str += f"|{via_norm}"
        
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _generate_key_from_coords(self, lon1, lat1, lon2, lat2, via_lon=None, via_lat=None):
        """
        Génère une clé unique pour un trajet basée sur les coordonnées.
        Utilisé comme fallback si les noms de villes ne sont pas disponibles.
        
        Args:
            lon1, lat1: Coordonnées d'origine
            lon2, lat2: Coordonnées de destination
            via_lon, via_lat: Coordonnées du point de passage (optionnel)
        
        Returns:
            str: Clé MD5 du trajet
        """
        coords = f"{lon1:.6f},{lat1:.6f}|{lon2:.6f},{lat2:.6f}"
        if via_lon is not None and via_lat is not None and not pd.isna(via_lon) and not pd.isna(via_lat):
            coords += f"|{via_lon:.6f},{via_lat:.6f}"
        return hashlib.md5(coords.encode()).hexdigest()
    
    def get(self, origin, destination, via=None, lon1=None, lat1=None, lon2=None, lat2=None, 
            via_lon=None, via_lat=None):
        """
        Récupère un trajet depuis le cache.
        Essaie d'abord avec les noms de villes, puis avec les coordonnées.
        
        Args:
            origin: Nom de la ville d'origine
            destination: Nom de la ville de destination
            via: Nom de la ville intermédiaire (optionnel)
            lon1, lat1: Coordonnées d'origine (fallback)
            lon2, lat2: Coordonnées de destination (fallback)
            via_lon, via_lat: Coordonnées du point de passage (fallback)
        
        Returns:
            tuple: (data, from_cache) où from_cache est True si trouvé dans le cache
        """
        # Essayer d'abord avec les noms de villes normalisés
        key = self._generate_key(origin, destination, via)
        if key and key in self.cache:
            self.stats['cache_hits'] += 1
            return self.cache[key], True
        
        # Fallback sur les coordonnées si disponibles
        if all(x is not None for x in [lon1, lat1, lon2, lat2]):
            key_coords = self._generate_key_from_coords(lon1, lat1, lon2, lat2, via_lon, via_lat)
            if key_coords in self.cache:
                self.stats['cache_hits'] += 1
                # Si trouvé par coordonnées, mettre à jour avec la clé par nom pour futures recherches
                if key:
                    self.cache[key] = self.cache[key_coords]
                return self.cache[key_coords], True
        
        return None, False
    
    def set(self, origin, destination, via, lon1, lat1, lon2, lat2, via_lon, via_lat, data):
        """
        Ajoute un trajet dans le cache avec les deux types de clés (noms et coordonnées).
        
        Args:
            origin: Nom de la ville d'origine
            destination: Nom de la ville de destination
            via: Nom de la ville intermédiaire (optionnel)
            lon1, lat1: Coordonnées d'origine
            lon2, lat2: Coordonnées de destination
            via_lon, via_lat: Coordonnées du point de passage (optionnel)
            data: Données à mettre en cache
        """
        # Stocker avec la clé basée sur les noms
        key = self._generate_key(origin, destination, via)
        if key:
            self.cache[key] = data
        
        # Stocker aussi avec la clé basée sur les coordonnées (pour compatibilité)
        key_coords = self._generate_key_from_coords(lon1, lat1, lon2, lat2, via_lon, via_lat)
        self.cache[key_coords] = data
    
    def save(self):
        """Sauvegarde le cache dans un fichier JSON."""
        if not self.cache:
            print("Cache vide, aucune sauvegarde effectuée")
            return
        
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
        print(f"Cache sauvegardé : {len(self.cache)} entrées dans '{self.cache_file}'")


def call_signal_api(lon1, lat1, lon2, lat2, via_lon=None, via_lat=None):
    """
    Appelle l'API Signal pour obtenir l'itinéraire ferroviaire.
    
    Args:
        lon1, lat1: Coordonnées d'origine
        lon2, lat2: Coordonnées de destination
        via_lon, via_lat: Point de passage intermédiaire (optionnel)
    
    Returns:
        dict: Réponse JSON de l'API
    """
    # Construire la liste de coordonnées
    coords = [f"{lon1},{lat1}"]
    if via_lon is not None and via_lat is not None and not pd.isna(via_lon) and not pd.isna(via_lat):
        coords.append(f"{via_lon},{via_lat}")
    coords.append(f"{lon2},{lat2}")
    
    url = f"{BASE_URL}/{';'.join(coords)}"
    params = {
        "overview": "full",
        "alternatives": "true",
        "steps": "true"
    }
    
    response = requests.get(url, params=params, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Erreur API Signal : code {response.status_code}")
    
    return response.json()


def detect_line_type(classes):
    """
    Détermine le type de ligne ferroviaire à partir des classes.
    
    Args:
        classes: Set de classes de l'intersection
    
    Returns:
        str: 'LGV', 'TER', ou 'Unknown'
    """
    # LGV : Ligne à Grande Vitesse
    # Indicateurs : vitesse élevée (>200 km/h), usage 'main', railway 'high_speed'
    lgv_indicators = {'high_speed', 'highspeed', 'lgv', 'main'}
    
    # TER : Transport Express Régional
    # Indicateurs : usage 'regional', 'branch', vitesse modérée
    ter_indicators = {'regional', 'branch', 'secondary'}
    
    classes_lower = {c.lower() for c in classes}
    
    if classes_lower & lgv_indicators:
        return 'LGV'
    elif classes_lower & ter_indicators:
        return 'TER'
    
    # Vérifier les informations de vitesse si disponibles
    for c in classes:
        if 'maxspeed' in c.lower():
            # Extraire la vitesse si possible
            try:
                speed = int(''.join(filter(str.isdigit, c)))
                if speed >= 200:
                    return 'LGV'
                elif speed < 160:
                    return 'TER'
            except:
                pass
    
    return 'Unknown'


def extract_route_statistics(signal_json):
    """
    Extrait les statistiques d'un itinéraire depuis la réponse de l'API Signal.
    
    Args:
        signal_json: Réponse JSON de l'API Signal
    
    Returns:
        dict: Statistiques du trajet (distance, types de lignes)
    """
    if not signal_json.get("routes") or not signal_json["routes"]:
        raise ValueError("Aucune route trouvée dans la réponse API")
    
    steps = signal_json["routes"][0]["legs"][0]["steps"]
    
    total_m = 0
    lgv_m = 0
    ter_m = 0
    unknown_m = 0
    
    for step in steps:
        distance = step["distance"]
        total_m += distance
        
        # Collecter toutes les classes de toutes les intersections
        all_classes = set()
        for intersection in step.get("intersections", []):
            all_classes.update(intersection.get("classes", []))
        
        # Déterminer le type de ligne
        line_type = detect_line_type(all_classes)
        
        if line_type == 'LGV':
            lgv_m += distance
        elif line_type == 'TER':
            ter_m += distance
        else:
            unknown_m += distance
    
    return {
        "distance_km": round(total_m / 1000, 2),
        "lgv_km": round(lgv_m / 1000, 2),
        "ter_km": round(ter_m / 1000, 2),
        "unknown_km": round(unknown_m / 1000, 2),
        "lgv_pct": round(100 * lgv_m / total_m, 1) if total_m > 0 else 0,
        "ter_pct": round(100 * ter_m / total_m, 1) if total_m > 0 else 0
    }


def collect_unique_trips(df, origin_col, dest_col, via_col=None):
    """
    Collecte tous les trajets uniques du DataFrame.
    
    Args:
        df: DataFrame pandas
        origin_col: Nom de la colonne d'origine
        dest_col: Nom de la colonne de destination
        via_col: Nom de la colonne via (optionnel)
    
    Returns:
        dict: Dictionnaire {clé_normalisée: indices_lignes}
    """
    unique_trips = {}
    
    for idx, row in df.iterrows():
        origin = TripCache.normalize_city_name(row.get(origin_col))
        destination = TripCache.normalize_city_name(row.get(dest_col))
        via = TripCache.normalize_city_name(row.get(via_col)) if via_col else None
        
        # Ignorer les trajets invalides
        if origin is None or destination is None:
            continue
        
        # Créer une clé unique
        key = f"{origin}|{destination}"
        if via:
            key += f"|{via}"
        
        if key not in unique_trips:
            unique_trips[key] = []
        unique_trips[key].append(idx)
    
    return unique_trips


def process_excel(input_file, output_file, cache_file="trip_cache.json",
                  origin_name_col="Depart", dest_name_col="Destination", via_name_col=None):
    """
    Traite un fichier Excel avec des trajets ferroviaires et ajoute les statistiques.
    Optimisé pour traiter uniquement les trajets uniques et maximiser l'utilisation du cache.
    
    NORMALISATION DES NOMS DE VILLES :
    Les noms sont normalisés pour maximiser les hits du cache :
    - "Paris" → "PARIS"
    - "New-York" → "NEW YORK"
    - "Saint  Étienne" → "SAINT ÉTIENNE"
    - "saint-malo" → "SAINT MALO"
    
    EXCLUSIONS :
    - Les entrées "not found" (quelle que soit la casse) sont ignorées
    
    Args:
        input_file: Chemin du fichier Excel d'entrée
        output_file: Chemin du fichier Excel de sortie
        cache_file: Chemin du fichier de cache JSON
        origin_name_col: Nom de la colonne contenant le nom de la ville d'origine
        dest_name_col: Nom de la colonne contenant le nom de la ville de destination
        via_name_col: Nom de la colonne contenant le nom de la ville intermédiaire (optionnel)
    
    Returns:
        pd.DataFrame: DataFrame avec les statistiques ajoutées
    """
    print(f"Lecture du fichier Excel : {input_file}")
    df = pd.read_excel(input_file)
    print(f"Trouvé {len(df)} trajets à traiter")
    print(f"Colonnes disponibles : {list(df.columns)}")
    
    # Vérifier les colonnes requises
    required_cols = [origin_name_col, dest_name_col,
                     f"{origin_name_col}_Longitude", f"{origin_name_col}_Latitude",
                     f"{dest_name_col}_Longitude", f"{dest_name_col}_Latitude"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le fichier : {missing_cols}")
    
    # Initialiser le cache
    cache = TripCache(cache_file)
    
    # PHASE 1 : Collecter les trajets uniques
    print("\n" + "="*50)
    print("PHASE 1 : Collection des trajets uniques")
    print("="*50)
    unique_trips = collect_unique_trips(df, origin_name_col, dest_name_col, via_name_col)
    print(f"Nombre de trajets uniques à traiter : {len(unique_trips)}")
    
    # PHASE 2 : Traiter chaque trajet unique
    print("\n" + "="*50)
    print("PHASE 2 : Traitement des trajets uniques")
    print("="*50)
    
    # Dictionnaire pour stocker les résultats par clé de trajet
    trip_results = {}
    
    for trip_idx, (trip_key, row_indices) in enumerate(unique_trips.items(), 1):
        # Prendre la première ligne pour ce trajet unique
        first_idx = row_indices[0]
        row = df.iloc[first_idx]
        
        origin_name = row[origin_name_col]
        dest_name = row[dest_name_col]
        via_name = row.get(via_name_col) if via_name_col else None
        
        origin_lon = row[f"{origin_name_col}_Longitude"]
        origin_lat = row[f"{origin_name_col}_Latitude"]
        dest_lon = row[f"{dest_name_col}_Longitude"]
        dest_lat = row[f"{dest_name_col}_Latitude"]
        
        via_lon = row.get(f"{via_name_col}_Longitude") if via_name_col else None
        via_lat = row.get(f"{via_name_col}_Latitude") if via_name_col else None
        
        print(f"[{trip_idx}/{len(unique_trips)}] {origin_name} → {dest_name}", end="")
        if via_name and not pd.isna(via_name):
            print(f" (via {via_name})", end="")
        
        try:
            # Vérifier le cache
            cached_result, from_cache = cache.get(
                origin_name, dest_name, via_name,
                origin_lon, origin_lat, dest_lon, dest_lat,
                via_lon, via_lat
            )
            
            if from_cache:
                print(" [CACHE]")
                stats = cached_result
            else:
                # Appel API
                print(" [API]", end="", flush=True)
                signal_json = call_signal_api(
                    origin_lon, origin_lat,
                    dest_lon, dest_lat,
                    via_lon, via_lat
                )
                stats = extract_route_statistics(signal_json)
                
                # Mettre en cache
                cache.set(
                    origin_name, dest_name, via_name,
                    origin_lon, origin_lat, dest_lon, dest_lat,
                    via_lon, via_lat, stats
                )
                cache.stats['api_calls'] += 1
                print(f" ✓ {stats['distance_km']} km (LGV: {stats['lgv_pct']}%)")
                
                # Respecter les serveurs (1 seconde entre les requêtes API)
                time.sleep(1)
        
        except Exception as e:
            print(f" ✗ Erreur : {e}")
            cache.stats['failures'] += 1
            stats = {
                "distance_km": None,
                "lgv_km": None,
                "ter_km": None,
                "unknown_km": None,
                "lgv_pct": None,
                "ter_pct": None
            }
        
        # Stocker le résultat pour toutes les lignes de ce trajet
        trip_results[trip_key] = stats
    
    # PHASE 3 : Appliquer les résultats au DataFrame
    print("\n" + "="*50)
    print("PHASE 3 : Application des résultats au DataFrame")
    print("="*50)
    
    # Créer les colonnes de résultats
    result_columns = {
        "distance_km": [],
        "lgv_km": [],
        "ter_km": [],
        "unknown_km": [],
        "lgv_pct": [],
        "ter_pct": []
    }
    
    for idx, row in df.iterrows():
        origin = TripCache.normalize_city_name(row.get(origin_name_col))
        destination = TripCache.normalize_city_name(row.get(dest_name_col))
        via = TripCache.normalize_city_name(row.get(via_name_col)) if via_name_col else None
        
        # Créer la clé
        if origin and destination:
            key = f"{origin}|{destination}"
            if via:
                key += f"|{via}"
            
            # Récupérer les résultats
            if key in trip_results:
                stats = trip_results[key]
            else:
                stats = {
                    "distance_km": None,
                    "lgv_km": None,
                    "ter_km": None,
                    "unknown_km": None,
                    "lgv_pct": None,
                    "ter_pct": None
                }
        else:
            stats = {
                "distance_km": None,
                "lgv_km": None,
                "ter_km": None,
                "unknown_km": None,
                "lgv_pct": None,
                "ter_pct": None
            }
        
        for col in result_columns:
            result_columns[col].append(stats[col])
    
    # Ajouter les colonnes au DataFrame
    for col, values in result_columns.items():
        df[col] = values
    
    print(f"Résultats appliqués à {len(df)} lignes")
    
    # Sauvegarder
    print(f"\nSauvegarde des résultats dans : {output_file}")
    df.to_excel(output_file, index=False)
    
    cache.save()
    
    # Afficher les statistiques finales
    total_rows = len(df)
    saved_calls = total_rows - len(unique_trips)
    
    print("\n" + "="*50)
    print("STATISTIQUES FINALES")
    print("="*50)
    print(f"Trajets uniques traités      : {len(unique_trips)}")
    print(f"Résultats depuis le cache    : {cache.stats['cache_hits']}")
    print(f"Appels API effectués         : {cache.stats['api_calls']}")
    print(f"Échecs                       : {cache.stats['failures']}")
    print(f"Total de lignes dans le fichier : {total_rows}")
    if len(unique_trips) > 0:
        print(f"Taux de succès               : {((cache.stats['cache_hits'] + cache.stats['api_calls']) / len(unique_trips) * 100):.1f}%")
    print("="*50)
    print(f"\nOPTIMISATION : {saved_calls} appels évités grâce au traitement des trajets uniques")
    print(f"(au lieu de {total_rows} appels API, seulement {len(unique_trips)} effectués)")
    print("="*50)
    print("Terminé !")
    
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 signal-batch-distances-optimized.py <input_excel> [output_excel] [cache_file]")
        print("\nExemples:")
        print("  python3 signal-batch-distances-optimized.py trajets.xlsx")
        print("  python3 signal-batch-distances-optimized.py trajets.xlsx resultats.xlsx")
        print("  python3 signal-batch-distances-optimized.py trajets.xlsx resultats.xlsx my_cache.json")
        print("\nNote: Ce script utilise les colonnes 'Depart' et 'Destination' par défaut")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    cache_file = sys.argv[3] if len(sys.argv) > 3 else "trip_cache.json"
    
    # Définir le nom de fichier de sortie par défaut
    if output_file is None:
        base_name = Path(input_file).stem
        output_file = f"{base_name}_with_distances.xlsx"
    
    try:
        process_excel(input_file, output_file, cache_file)
    except FileNotFoundError:
        print(f"Erreur : Fichier '{input_file}' introuvable")
        sys.exit(1)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)