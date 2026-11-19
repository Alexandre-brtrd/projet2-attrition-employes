"""Historique des prédictions, conservé dans un fichier CSV."""

import csv
import os

from backend.exceptions import DonneeInvalideError

# frontend/historique_predictions.csv (créé à la première prédiction, ignoré par Git).
CHEMIN_HISTORIQUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historique_predictions.csv")
COLONNES_HISTORIQUE = ["date", "risque_depart", "conclusion", "champs_renseignes",
                       "precision_attendue", "saisies"]


class Historique:
    """Ajoute et relit les prédictions dans un fichier CSV (une ligne par prédiction)."""

    def __init__(self, chemin: str = CHEMIN_HISTORIQUE) -> None:
        """Reçoit le chemin du fichier ; il est créé à la première prédiction."""
        self._chemin = chemin

    def ajouter(self, ligne: dict[str, str]) -> None:
        """Ajoute une ligne à la fin du fichier (avec l'en-tête si le fichier est neuf).

        Lève DonneeInvalideError s'il manque une colonne dans ligne.
        """
        manquantes = [nom for nom in COLONNES_HISTORIQUE if nom not in ligne]
        if manquantes:
            raise DonneeInvalideError(f"Ligne d'historique incomplète : {', '.join(manquantes)}")
        dossier = os.path.dirname(self._chemin)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        nouveau = not os.path.exists(self._chemin) or os.path.getsize(self._chemin) == 0
        with open(self._chemin, "a", encoding="utf-8", newline="") as fichier:
            ecrivain = csv.DictWriter(fichier, fieldnames=COLONNES_HISTORIQUE, extrasaction="ignore")
            if nouveau:
                ecrivain.writeheader()
            ecrivain.writerow(ligne)

    def lire(self) -> list[dict[str, str]]:
        """Renvoie les prédictions enregistrées, de la plus récente à la plus ancienne.

        Renvoie une liste vide si le fichier n'existe pas encore ; lève DonneeInvalideError
        si le fichier n'a pas le format attendu.
        """
        if not os.path.exists(self._chemin):
            return []
        with open(self._chemin, encoding="utf-8", newline="") as fichier:
            try:
                lignes = list(csv.DictReader(fichier))
            except csv.Error as erreur:
                raise DonneeInvalideError(f"Historique illisible : {erreur}") from None
        if lignes and set(COLONNES_HISTORIQUE) - set(lignes[0]):
            raise DonneeInvalideError(f"L'historique {self._chemin} n'a pas les colonnes attendues.")
        return sorted(lignes, key=lambda ligne: ligne["date"], reverse=True)

    def effacer(self) -> None:
        """Supprime le fichier d'historique s'il existe."""
        if os.path.exists(self._chemin):
            os.remove(self._chemin)

    def __len__(self) -> int:
        return len(self.lire())

    def __repr__(self) -> str:
        return f"Historique(chemin={os.path.basename(self._chemin)!r})"
