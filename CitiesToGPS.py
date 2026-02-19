import pandas as pd
from geopy.geocoders import Nominatim
import time
import sys
from pathlib import Path


class GeocodingCache:
    """Gère un cache persistant des coordonnées géographiques."""
    
    def __init__(self, cache_file="geocoding_cache.xlsx"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
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
        normalized = str(city_name).upper().strip()
        # Remplacer les tirets par des espaces
        normalized = normalized.replace('-', ' ')
        # Normaliser les espaces multiples en un seul espace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _load_cache(self):
        """Charge le cache depuis le fichier Excel s'il existe."""
        if Path(self.cache_file).exists():
            try:
                df = pd.read_excel(self.cache_file)
                print(f"Cache chargé : {len(df)} entrées trouvées dans '{self.cache_file}'")
                # Normaliser les noms lors du chargement
                cache_dict = {}
                for _, row in df.iterrows():
                    normalized_name = self.normalize_city_name(row['city_name'])
                    cache_dict[normalized_name] = {
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    }
                return cache_dict
            except Exception as e:
                print(f"Avertissement : Impossible de charger le cache : {e}")
                return {}
        else:
            print(f"Aucun cache trouvé. Un nouveau sera créé : '{self.cache_file}'")
            return {}
    
    def get(self, city_name):
        """Récupère les coordonnées depuis le cache."""
        normalized_name = self.normalize_city_name(city_name)
        if normalized_name in self.cache:
            data = self.cache[normalized_name]
            return data['latitude'], data['longitude']
        return None, None
    
    def set(self, city_name, latitude, longitude):
        """Ajoute ou met à jour une entrée dans le cache."""
        normalized_name = self.normalize_city_name(city_name)
        self.cache[normalized_name] = {
            'latitude': latitude,
            'longitude': longitude
        }
    
    def save(self):
        """Sauvegarde le cache dans un fichier Excel."""
        if not self.cache:
            print("Cache vide, aucune sauvegarde effectuée")
            return
        
        cache_df = pd.DataFrame([
            {'city_name': city, 'latitude': data['latitude'], 'longitude': data['longitude']}
            for city, data in self.cache.items()
        ])
        cache_df.to_excel(self.cache_file, index=False)
        print(f"Cache sauvegardé : {len(cache_df)} entrées dans '{self.cache_file}'")


def get_coordinates(city_name, geolocator, cache, timeout=10):
    """
    Obtient les coordonnées GPS d'une ville en utilisant le cache ou Nominatim.
    
    Args:
        city_name: Nom de la ville
        geolocator: Instance de Nominatim
        cache: Instance de GeocodingCache
        timeout: Délai d'attente maximum pour la requête
    
    Returns:
        tuple: (latitude, longitude, from_cache) ou (None, None, from_cache) si introuvable
    """
    # Vérifier d'abord le cache
    lat, lon = cache.get(city_name)
    if lat is not None:
        return lat, lon, True  # True = trouvé dans le cache
    
    # Si pas dans le cache, effectuer la recherche
    try:
        location = geolocator.geocode(city_name, timeout=timeout)
        if location:
            lat, lon = location.latitude, location.longitude
            cache.set(city_name, lat, lon)
            return lat, lon, False  # False = recherche API effectuée
        else:
            print(f"Avertissement : Coordonnées introuvables pour '{city_name}'")
            cache.set(city_name, None, None)
            return None, None, False
    except Exception as e:
        print(f"Erreur lors du géocodage de '{city_name}' : {e}")
        return None, None, False


def collect_unique_cities(df, city_columns, cache):
    """
    Collecte toutes les villes uniques des colonnes spécifiées.
    Les noms sont normalisés selon les règles du cache.
    Ignore les entrées "not found".
    
    Args:
        df: DataFrame pandas
        city_columns: Liste des noms de colonnes contenant des villes
        cache: Instance de GeocodingCache pour la normalisation
    
    Returns:
        set: Ensemble de noms de villes uniques normalisés (non vides, hors "not found")
    """
    unique_cities = set()
    for col in city_columns:
        if col in df.columns:
            cities = df[col].dropna().astype(str).str.strip()
            for city in cities[cities != '']:
                normalized = cache.normalize_city_name(city)
                # Ignorer "not found" et ses variantes après normalisation
                if normalized and normalized != 'NOT FOUND':
                    unique_cities.add(normalized)
    return unique_cities


def excel_cities_to_gps(input_file, output_file=None, cache_file="geocoding_cache.xlsx", 
                        user_agent="city_to_gps", city_columns=None):
    """
    Lit un fichier Excel avec des noms de villes et ajoute les coordonnées GPS.
    Optimisé pour traiter uniquement les villes uniques et minimiser les appels API.
    
    NORMALISATION DES NOMS DE VILLES :
    Les noms sont normalisés pour maximiser les hits du cache :
    - "Paris" → "PARIS"
    - "New-York" → "NEW YORK"
    - "Saint  Étienne" → "SAINT ÉTIENNE"
    - "saint-malo" → "SAINT MALO"
    
    EXCLUSIONS :
    - Les entrées "not found" (quelle que soit la casse) sont ignorées et ne sont pas géocodées
    
    Args:
        input_file: Chemin du fichier Excel d'entrée
        output_file: Chemin du fichier Excel de sortie (par défaut: input_file_with_GPS.xlsx)
        cache_file: Chemin du fichier de cache (par défaut: geocoding_cache.xlsx)
        user_agent: User agent pour Nominatim (requis par OpenStreetMap)
        city_columns: Liste des colonnes contenant des villes (par défaut: ['Depart', 'Destination'])
    
    Returns:
        pd.DataFrame: DataFrame avec les coordonnées ajoutées
    """
    # Définir les colonnes de villes par défaut
    if city_columns is None:
        city_columns = ['Depart', 'Destination']
    
    # Définir le nom de fichier de sortie par défaut
    if output_file is None:
        base_name = Path(input_file).stem
        output_file = f"{base_name}_with_GPS.xlsx"
    
    # Charger le fichier Excel
    print(f"Lecture du fichier Excel : {input_file}")
    df = pd.read_excel(input_file)
    print(f"Trouvé {len(df)} lignes avec les colonnes : {list(df.columns)}")
    
    # Vérifier que les colonnes existent
    missing_columns = [col for col in city_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Colonnes manquantes dans le fichier : {missing_columns}")
    
    print(f"\nColonnes à géocoder : {city_columns}")
    
    # Initialiser le cache et le géocodeur
    cache = GeocodingCache(cache_file)
    geolocator = Nominatim(user_agent=user_agent)
    
    # OPTIMISATION : Collecter toutes les villes uniques
    print("\n" + "="*50)
    print("PHASE 1 : Collection des villes uniques")
    print("="*50)
    unique_cities = collect_unique_cities(df, city_columns, cache)
    print(f"Nombre de villes uniques à géocoder : {len(unique_cities)}")
    
    # Statistiques
    stats = {'cache_hits': 0, 'api_calls': 0, 'failures': 0}
    
    # OPTIMISATION : Créer un dictionnaire de coordonnées pour toutes les villes uniques
    print("\n" + "="*50)
    print("PHASE 2 : Géocodage des villes uniques")
    print("="*50)
    coordinates_map = {}
    
    for idx, city_name in enumerate(sorted(unique_cities), 1):
        print(f"[{idx}/{len(unique_cities)}] Géocodage de '{city_name}'...", end="", flush=True)
        lat, lon, from_cache = get_coordinates(city_name, geolocator, cache)
        
        coordinates_map[city_name] = {'latitude': lat, 'longitude': lon}
        
        if lat is not None:
            if from_cache:
                print(f" ✓ ({lat:.4f}, {lon:.4f}) [CACHE]")
                stats['cache_hits'] += 1
            else:
                print(f" ✓ ({lat:.4f}, {lon:.4f}) [API]")
                stats['api_calls'] += 1
                # Respecter les serveurs OpenStreetMap (1 seconde entre les requêtes API)
                time.sleep(1)
        else:
            print(" ✗ Échec")
            stats['failures'] += 1
    
    # PHASE 3 : Appliquer les coordonnées au DataFrame
    print("\n" + "="*50)
    print("PHASE 3 : Application des coordonnées au DataFrame")
    print("="*50)
    
    for col in city_columns:
        latitude_col = f"{col}_Latitude"
        longitude_col = f"{col}_Longitude"
        
        print(f"Traitement de la colonne : {col}")
        
        # Appliquer les coordonnées en une seule opération vectorisée
        # avec normalisation des noms pour le lookup
        # Ignorer les entrées "not found"
        def get_lat(x):
            if pd.notna(x):
                normalized = cache.normalize_city_name(x)
                if normalized != 'NOT FOUND':
                    return coordinates_map.get(normalized, {}).get('latitude')
            return None
        
        def get_lon(x):
            if pd.notna(x):
                normalized = cache.normalize_city_name(x)
                if normalized != 'NOT FOUND':
                    return coordinates_map.get(normalized, {}).get('longitude')
            return None
        
        df[latitude_col] = df[col].apply(get_lat)
        df[longitude_col] = df[col].apply(get_lon)
        
        # Compter les résultats
        not_found_count = (df[col].notna() & (df[col].astype(str).str.strip().str.upper() == 'NOT FOUND')).sum()
        success_count = df[latitude_col].notna().sum()
        total_count = df[col].notna().sum() - not_found_count
        
        if not_found_count > 0:
            print(f"  → {success_count}/{total_count} villes géocodées avec succès ({not_found_count} 'not found' ignorés)")
        else:
            print(f"  → {success_count}/{total_count} villes géocodées avec succès")
    
    # Sauvegarder les résultats et le cache
    print(f"\nSauvegarde des résultats dans : {output_file}")
    df.to_excel(output_file, index=False)
    
    cache.save()
    
    # Afficher les statistiques finales
    print("\n" + "="*50)
    print("STATISTIQUES FINALES")
    print("="*50)
    print(f"Villes uniques traitées   : {len(unique_cities)}")
    print(f"Résultats depuis le cache : {stats['cache_hits']}")
    print(f"Appels API effectués      : {stats['api_calls']}")
    print(f"Échecs                    : {stats['failures']}")
    print(f"Taux de succès            : {((stats['cache_hits'] + stats['api_calls']) / len(unique_cities) * 100):.1f}%")
    print("="*50)
    
    # Calculer le gain d'optimisation
    total_rows = df[city_columns].notna().sum().sum()
    saved_calls = total_rows - len(unique_cities)
    print(f"\nOPTIMISATION : {saved_calls} appels évités grâce au traitement des villes uniques")
    print(f"(au lieu de {total_rows} géocodages, seulement {len(unique_cities)} effectués)")
    print("="*50)
    print("Terminé !")
    
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 cities-to-GPS-optimized.py <input_excel_file> [output_excel_file] [cache_file]")
        print("\nExemples:")
        print("  python3 cities-to-GPS-optimized.py trajets.xlsx")
        print("  python3 cities-to-GPS-optimized.py trajets.xlsx results.xlsx")
        print("  python3 cities-to-GPS-optimized.py trajets.xlsx results.xlsx my_cache.xlsx")
        print("\nNote: Ce script géocode uniquement les colonnes 'Depart' et 'Destination'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    cache_file = sys.argv[3] if len(sys.argv) > 3 else "geocoding_cache.xlsx"
    
    try:
        excel_cities_to_gps(input_file, output_file, cache_file)
    except FileNotFoundError:
        print(f"Erreur : Fichier '{input_file}' introuvable")
        sys.exit(1)
    except ValueError as e:
        print(f"Erreur : {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur : {e}")
        sys.exit(1)