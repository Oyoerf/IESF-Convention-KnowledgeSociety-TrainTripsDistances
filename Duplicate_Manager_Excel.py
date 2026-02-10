import pandas as pd
import sys

def supprimer_doublons_trajets(fichier_entree, fichier_sortie=None):
    """
    Supprime les doublons de trajets entre références différentes pour une même personne.
    Conserve tous les trajets au sein d'une même référence (y compris les doublons aller-retour),
    mais supprime les trajets des références suivantes s'ils existent déjà sous une autre référence.
    
    Paramètres:
        fichier_entree (str): Chemin du fichier Excel d'entrée
        fichier_sortie (str): Chemin du fichier Excel de sortie (optionnel)
    """
    if fichier_sortie is None:
        fichier_sortie = fichier_entree.replace('.xlsx', '_sans_doublons.xlsx')
    
    df = pd.read_excel(fichier_entree)
    
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
    
    nb_lignes_apres = len(df_unique)
    nb_doublons_supprimes = nb_lignes_avant - nb_lignes_apres
    
    df_unique.to_excel(fichier_sortie, index=False)
    
    print(f"Traitement terminé :")
    print(f"  - Lignes initiales : {nb_lignes_avant}")
    print(f"  - Lignes finales : {nb_lignes_apres}")
    print(f"  - Doublons supprimés : {nb_doublons_supprimes}")
    print(f"  - Fichier généré : {fichier_sortie}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python supprimer_doublons.py <fichier_entree.xlsx> [fichier_sortie.xlsx]")
        sys.exit(1)
    
    fichier_entree = sys.argv[1]
    fichier_sortie = sys.argv[2] if len(sys.argv) > 2 else None
    
    supprimer_doublons_trajets(fichier_entree, fichier_sortie)