"""Point d'entrée du projet.

    python main.py             ouvre l'interface graphique
    python main.py entrainer   entraîne le modèle et l'enregistre dans backend/sauvegarde/
"""

import argparse
import os
import sys

CHEMIN_EXIGENCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")


def message_module_manquant(erreur: ModuleNotFoundError) -> str:
    """Explique quelle bibliothèque manque et comment l'installer avec le Python réellement utilisé."""
    return (f"Bibliothèque manquante ou incomplète : {erreur.name}\n"
            f"Python utilisé : {sys.executable}\n"
            f"Installez les dépendances avec ce même Python :\n"
            f'    "{sys.executable}" -m pip install -r "{CHEMIN_EXIGENCES}"\n'
            f"Si l'erreur persiste, ajoutez --force-reinstall à la fin de la commande.")


try:
    from backend.entrainement import entrainer_et_sauvegarder, resume_entrainement
    from backend.exceptions import ErreurProjet
except ModuleNotFoundError as erreur:  # numpy, pandas, scikit-learn ou matplotlib absent
    sys.exit(message_module_manquant(erreur))


def main(arguments: list[str] | None = None) -> int:
    """Analyse la ligne de commande, exécute la commande demandée et renvoie le code de sortie."""
    analyseur = argparse.ArgumentParser(
        description="Estimation du risque de départ d'un employé (INF1007, projet 2).")
    analyseur.add_argument("commande", nargs="?", choices=["interface", "entrainer"],
                           default="interface", help="interface (par défaut) ou entrainer")
    options = analyseur.parse_args(arguments)

    if options.commande == "entrainer":
        print("Entraînement en cours (environ 30 secondes)...")
        try:
            metadonnees = entrainer_et_sauvegarder()
        except ErreurProjet as erreur:
            print(f"Erreur : {erreur}", file=sys.stderr)
            return 1
        print(resume_entrainement(metadonnees))
        return 0

    # Import tardif : l'entraînement fonctionne même sans interface graphique (ex. serveur de CI).
    try:
        from frontend.fenetre import lancer_interface
    except ModuleNotFoundError as erreur:  # customtkinter absent
        print(message_module_manquant(erreur), file=sys.stderr)
        return 1
    lancer_interface()
    return 0


if __name__ == "__main__":
    sys.exit(main())
