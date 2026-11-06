"""Logique de l'application : relie le modèle, les variables et l'historique.

L'interface graphique n'appelle que cette classe ; elle ne contient aucun calcul.
"""

import json
import os
from collections.abc import Iterable
from datetime import datetime

import numpy as np
import pandas as pd

from frontend.historique import CHEMIN_HISTORIQUE, Historique
from backend.modeles import Modele
from backend.metriques import exactitude_equilibree
from backend.saisie_partielle import effets_champs, risques_partiels
from backend.config import (DOSSIER_SAUVEGARDE, EXPLICATIONS, GROUPES, NOM_JEU_TEST, NOM_METADONNEES,
                            NOM_MODELE, NOM_REFERENCE, REGLES_COHERENCE, SEUIL_DECISION)
from backend.exceptions import DonneeInvalideError, SaisieInvalideError
from backend.jeu_de_donnees import lire_csv, lire_json
from backend.variables import NON_RENSEIGNE, Variable, VariableCategorielle, variable_depuis_dict

# Bornes supérieures (exclues) des niveaux de risque affichés.
NIVEAUX_RISQUE = [(0.30, "faible"), (0.50, "modéré"), (0.70, "élevé"), (float("inf"), "très élevé")]

# Une liste de choix devient une rangée de boutons si elle a au plus ce nombre de choix
# et si ses libellés courts tiennent ensemble dans ce nombre de caractères.
MAX_BOUTONS, MAX_CARACTERES_BOUTONS = 5, 32


def choix_en_boutons(variable: Variable) -> dict[str, str] | None:
    """Libellés courts des boutons d'une liste de choix, ou None si elle doit rester déroulante.

    Renvoie {libellé court affiché : texte accepté par variable.valider}. Pour une échelle,
    « 3 — Élevée » devient « Élevée ». Les nombres et les longues listes renvoient None.
    """
    if not isinstance(variable, VariableCategorielle):
        return None
    complets = variable.choix()
    courts = [texte.split(" — ", 1)[-1] for texte in complets]
    if len(courts) > MAX_BOUTONS or sum(len(texte) for texte in courts) > MAX_CARACTERES_BOUTONS:
        return None
    if len(set(courts)) != len(courts):
        return None
    return dict(zip(courts, complets))


def points(effet: float) -> str:
    """Écrit un effet (entre -1 et 1) en points de pourcentage signés : 0.183 -> « +18 pts »."""
    valeur = round(effet * 100)
    return f"{valeur:+d} pts" if valeur else "≈ 0 pt"


def pourcentage(valeur: float) -> str:
    """Écrit 0.684 sous la forme « 68 % » (typographie française) ; « < 1 % » et « > 99 % » aux extrêmes."""
    if 0 < valeur < 0.005:
        return "< 1 %"
    if 0.995 <= valeur < 1:
        return "> 99 %"
    return f"{valeur * 100:.0f} %"


class Prediction:
    """Résultat d'une prédiction, prêt à être affiché ou enregistré."""

    def __init__(self, probabilite: float, valeurs_connues: dict[str, object], nb_variables: int,
                 precision_attendue: float, effets: dict[str, float] | None = None,
                 date: datetime | None = None) -> None:
        """Reçoit le risque (0 à 1), les valeurs saisies, le nombre total de variables,
        la précision attendue, l'effet de chaque valeur et la date (maintenant par défaut).

        Lève ValueError si le risque ou la précision sort de [0, 1].
        """
        if not 0 <= probabilite <= 1 or not 0 <= precision_attendue <= 1:
            raise ValueError("Le risque et la précision doivent être entre 0 et 1.")
        self._probabilite = probabilite
        self._valeurs_connues = dict(valeurs_connues)
        self._nb_variables = nb_variables
        self._precision_attendue = precision_attendue
        self._effets = dict(effets or {})
        self._date = date or datetime.now()

    @property
    def probabilite(self) -> float:
        """Risque de départ estimé, entre 0 et 1."""
        return self._probabilite

    @property
    def precision_attendue(self) -> float:
        """Exactitude équilibrée mesurée sur le test avec les mêmes champs renseignés."""
        return self._precision_attendue

    @property
    def valeurs_connues(self) -> dict[str, object]:
        """Copie des valeurs saisies (champs renseignés seulement)."""
        return dict(self._valeurs_connues)

    @property
    def effets(self) -> dict[str, float]:
        """Copie de l'effet de chaque valeur saisie sur le risque."""
        return dict(self._effets)

    @property
    def nb_champs(self) -> int:
        """Nombre de champs renseignés."""
        return len(self._valeurs_connues)

    @property
    def nb_variables(self) -> int:
        """Nombre total de champs du formulaire."""
        return self._nb_variables

    @property
    def date(self) -> datetime:
        """Moment de la prédiction."""
        return self._date

    @property
    def depart_predit(self) -> bool:
        """Vrai si le risque atteint le seuil de décision (50 %)."""
        return self._probabilite >= SEUIL_DECISION

    @property
    def niveau(self) -> str:
        """Niveau de risque en mots : faible, modéré, élevé ou très élevé."""
        return next(nom for borne, nom in NIVEAUX_RISQUE if self._probabilite < borne)

    def conclusion(self) -> str:
        """Phrase courte pour un non-informaticien."""
        return "départ probable" if self.depart_predit else "maintien probable"

    def vers_ligne(self) -> dict[str, str]:
        """Renvoie la ligne à écrire dans l'historique CSV."""
        return {
            "date": self._date.isoformat(timespec="seconds"),
            "risque_depart": f"{self._probabilite:.3f}",
            "conclusion": self.conclusion(),
            "champs_renseignes": f"{self.nb_champs}/{self._nb_variables}",
            "precision_attendue": f"{self._precision_attendue:.3f}",
            "saisies": json.dumps(self._valeurs_connues, ensure_ascii=False),
        }

    def __str__(self) -> str:
        return (f"Risque de départ {self.niveau} ({pourcentage(self._probabilite)}) : "
                f"{self.conclusion()}. Précision attendue avec {self.nb_champs} champ(s) "
                f"sur {self._nb_variables} : {pourcentage(self._precision_attendue)}.")

    def __repr__(self) -> str:
        return f"Prediction(probabilite={self._probabilite:.3f}, champs={self.nb_champs})"


class Application:
    """Contient le modèle, les variables du formulaire, le jeu de test, les employés de
    référence et l'historique (composition)."""

    def __init__(self, modele: Modele, variables: list[Variable], X_test: pd.DataFrame, y_test,
                 reference: pd.DataFrame, metadonnees: dict, historique: Historique) -> None:
        """Assemble les composants.

        Lève DonneeInvalideError si les variables, le test ou la référence ne correspondent
        pas aux colonnes du modèle.
        """
        if sorted(variable.nom for variable in variables) != sorted(modele.colonnes):
            raise DonneeInvalideError("Les variables des métadonnées ne correspondent pas au modèle.")
        for description, tableau in (("Le jeu de test", X_test), ("L'échantillon de référence", reference)):
            absentes = [nom for nom in modele.colonnes if nom not in tableau.columns]
            if absentes or tableau.empty:
                raise DonneeInvalideError(f"{description} est vide ou incomplet {absentes}.")
        self._modele = modele
        self._variables = {variable.nom: variable for variable in variables}
        self._X_test = X_test[modele.colonnes].reset_index(drop=True)
        self._y_test = np.asarray(y_test).astype(int)
        self._reference = reference[modele.colonnes].reset_index(drop=True)
        self._metadonnees = metadonnees
        self._historique = historique
        self._cache_scores: dict[frozenset[str], np.ndarray] = {}
        self._scores_test: np.ndarray | None = None
        self._generateur = np.random.default_rng()

    @classmethod
    def depuis_fichiers(cls, dossier_sauvegarde: str = DOSSIER_SAUVEGARDE,
                        chemin_historique: str = CHEMIN_HISTORIQUE) -> "Application":
        """Construit l'application à partir des fichiers produits par l'entraînement.

        Lève FichierIntrouvableError si un fichier manque, DonneeInvalideError s'il est mal formé.
        """
        conseil = "Lancez d'abord l'entraînement : python main.py entrainer"
        modele = Modele.charger(os.path.join(dossier_sauvegarde, NOM_MODELE))
        metadonnees = lire_json(os.path.join(dossier_sauvegarde, NOM_METADONNEES), conseil)
        jeu_test = lire_csv(os.path.join(dossier_sauvegarde, NOM_JEU_TEST), conseil)
        reference = lire_csv(os.path.join(dossier_sauvegarde, NOM_REFERENCE), conseil)
        try:
            variables = [variable_depuis_dict(description) for description in metadonnees["variables"]]
            y_test = jeu_test.pop("Depart")
        except KeyError as erreur:
            raise DonneeInvalideError(f"Fichiers du modèle incomplets : clé {erreur} absente.") from None
        return cls(modele, variables, jeu_test, y_test, reference, metadonnees,
                   Historique(chemin_historique))

    @property
    def modele(self) -> Modele:
        """Modèle entraîné utilisé pour les prédictions."""
        return self._modele

    @property
    def variables(self) -> list[Variable]:
        """Variables du formulaire, dans l'ordre du modèle."""
        return list(self._variables.values())

    @property
    def metadonnees(self) -> dict:
        """Métadonnées écrites à l'entraînement (métriques, courbe de précision, etc.)."""
        return self._metadonnees

    @property
    def historique(self) -> Historique:
        """Historique des prédictions."""
        return self._historique

    def variable(self, nom: str) -> Variable:
        """Renvoie la variable nommée ; lève DonneeInvalideError si elle n'existe pas."""
        if nom not in self._variables:
            raise DonneeInvalideError(f"Variable inconnue : {nom}", nom)
        return self._variables[nom]

    def variables_par_groupe(self) -> dict[str, list[Variable]]:
        """Regroupe les variables par section du formulaire, dans l'ordre de config.GROUPES."""
        groupes: dict[str, list[Variable]] = {groupe: [] for groupe in GROUPES}
        for variable in self._variables.values():
            groupes.setdefault(variable.groupe, []).append(variable)
        return {groupe: liste for groupe, liste in groupes.items() if liste}

    def champs_conseilles(self, champs_connus: Iterable[str], nombre: int = 3) -> list[Variable]:
        """Les champs vides les plus utiles au modèle (selon l'importance mesurée à l'entraînement)."""
        connus = set(champs_connus)
        ordre = self._metadonnees.get("courbe_precision", {}).get("ordre", list(self._variables))
        return [self._variables[nom] for nom in ordre if nom not in connus and nom in self._variables][:nombre]

    def champs_renseignes(self, saisies: dict[str, str]) -> list[str]:
        """Noms des champs non vides, sans vérifier leur contenu (pour l'indicateur en direct)."""
        return [nom for nom in self._variables
                if (saisies.get(nom) or "").strip() not in ("", NON_RENSEIGNE)]

    def lire_saisies(self, saisies: dict[str, str]) -> dict[str, object]:
        """Valide tout le formulaire et renvoie {nom : valeur} pour les champs renseignés.

        Toutes les erreurs sont réunies dans une seule SaisieInvalideError, pour que
        l'utilisateur les voie toutes d'un coup.
        """
        valeurs, erreurs = {}, {}
        for nom in saisies:
            if nom not in self._variables:
                erreurs[nom] = f"Champ inconnu : {nom}"
        for nom, variable in self._variables.items():
            try:
                valeur = variable.lire(saisies.get(nom, ""))
            except DonneeInvalideError as erreur:
                erreurs[nom] = str(erreur)
            else:
                if valeur is not None:
                    valeurs[nom] = valeur
        for nom, message in self._verifier_coherence(valeurs).items():
            erreurs.setdefault(nom, message)
        if erreurs:
            raise SaisieInvalideError(erreurs)
        return valeurs

    def _verifier_coherence(self, valeurs: dict[str, object]) -> dict[str, str]:
        """Applique config.REGLES_COHERENCE aux champs renseignés ; renvoie {nom : message}."""
        erreurs = {}
        for petit, grand, ecart, message in REGLES_COHERENCE:
            if petit in valeurs and grand in valeurs and valeurs[petit] + ecart > valeurs[grand]:
                erreurs.setdefault(petit, f"Incohérence : {message} "
                                          f"({valeurs[petit]} contre {valeurs[grand]}).")
        return erreurs

    def explication(self, nom: str) -> str:
        """Explication en langage courant du champ (texte vide si son libellé suffit)."""
        return EXPLICATIONS.get(nom, "")

    def progression_par_groupe(self, saisies: dict[str, str]) -> dict[str, tuple[int, int]]:
        """{section du formulaire : (champs remplis, champs de la section)}, dans l'ordre des sections."""
        remplis = set(self.champs_renseignes(saisies))
        return {groupe: (sum(variable.nom in remplis for variable in variables), len(variables))
                for groupe, variables in self.variables_par_groupe().items()}

    def scores_selon_champs(self, champs_connus: Iterable[str]) -> np.ndarray:
        """Risque estimé de chaque employé du test quand seuls ces champs sont connus (mis en cache).

        C'est exactement le calcul fait pour l'utilisateur : les champs vides prennent les
        valeurs des employés de référence.
        """
        cle = frozenset(champs_connus) & frozenset(self._variables)
        if cle not in self._cache_scores:
            self._cache_scores[cle] = risques_partiels(self._modele, self._X_test, cle, self._reference)
        return self._cache_scores[cle].copy()

    def precision_attendue(self, champs_connus: Iterable[str]) -> float:
        """Exactitude équilibrée mesurée sur le test avec ces seuls champs renseignés."""
        scores = self.scores_selon_champs(champs_connus)
        return exactitude_equilibree(self._y_test, (scores >= SEUIL_DECISION).astype(int))

    def tranches_de_risque(self, champs_connus: Iterable[str], nb_tranches: int = 5) -> list[dict]:
        """Ce que le risque affiché veut dire en pratique, mesuré sur les employés du test.

        Découpe [0, 1] en nb_tranches tranches égales et renvoie, pour chacune :
        {"bas", "haut", "employes", "partis"} (avec les mêmes champs connus que l'utilisateur).
        Lève ValueError si nb_tranches < 1.
        """
        if nb_tranches < 1:
            raise ValueError("Il faut au moins une tranche.")
        scores = self.scores_selon_champs(champs_connus)
        rangs = np.minimum((scores * nb_tranches).astype(int), nb_tranches - 1)
        employes = np.bincount(rangs, minlength=nb_tranches)
        partis = np.bincount(rangs, weights=self._y_test, minlength=nb_tranches).astype(int)
        return [{"bas": rang / nb_tranches, "haut": (rang + 1) / nb_tranches,
                 "employes": int(employes[rang]), "partis": int(partis[rang])}
                for rang in range(nb_tranches)]

    def situer(self, prediction: "Prediction", nb_tranches: int = 5) -> dict:
        """Place la prédiction parmi les employés du test évalués avec les mêmes champs.

        Renvoie {"depasse": part des employés du test au risque plus bas (0 à 1),
        "tranche": la tranche de tranches_de_risque qui contient le risque}.
        """
        scores = self.scores_selon_champs(prediction.valeurs_connues)
        tranches = self.tranches_de_risque(prediction.valeurs_connues, nb_tranches)
        rang = min(int(prediction.probabilite * nb_tranches), nb_tranches - 1)
        return {"depasse": float(np.mean(scores < prediction.probabilite)), "tranche": tranches[rang]}

    def facteurs_principaux(self, prediction: "Prediction", nombre: int = 3) -> list[tuple[str, str, float]]:
        """Les champs qui pèsent le plus dans la prédiction : [(libellé, valeur saisie, effet)].

        Triés du plus fort au plus faible effet, en valeur absolue (la lambda sert de clé de tri).
        """
        valeurs = prediction.valeurs_connues
        effets = sorted(prediction.effets.items(), key=lambda paire: abs(paire[1]), reverse=True)
        return [(self.variable(nom).libelle, self.variable(nom).formater(valeurs[nom]), effet)
                for nom, effet in effets[:nombre] if nom in valeurs]

    def saisies_depuis_historique(self, ligne: dict[str, str]) -> dict[str, str]:
        """Textes à remettre dans le formulaire pour une ligne de l'historique.

        Les champs absents de la ligne restent vides. Lève DonneeInvalideError si la colonne
        « saisies » est illisible ou contient une variable inconnue.
        """
        try:
            valeurs = json.loads(ligne["saisies"])
        except (KeyError, TypeError, json.JSONDecodeError):
            raise DonneeInvalideError("Cette ligne de l'historique ne contient pas de saisies lisibles.") from None
        if not isinstance(valeurs, dict):
            raise DonneeInvalideError("Cette ligne de l'historique ne contient pas de saisies lisibles.")
        saisies = {nom: "" for nom in self._variables}
        for nom, valeur in valeurs.items():
            saisies[nom] = self.variable(nom).formater(valeur)
        return saisies

    def predire(self, saisies: dict[str, str], enregistrer: bool = True) -> Prediction:
        """Valide les saisies, prédit le risque et l'ajoute à l'historique.

        Lève SaisieInvalideError si une saisie est invalide, DonneeInvalideError si aucun champ
        n'est renseigné. Les champs vides prennent tour à tour les valeurs des employés de
        référence (voir saisie_partielle.py).
        """
        valeurs = self.lire_saisies(saisies)
        if not valeurs:
            raise DonneeInvalideError("Aucun champ renseigné : remplissez au moins un champ "
                                      "pour obtenir une prédiction.")
        profil = pd.DataFrame([valeurs])
        probabilite = float(risques_partiels(self._modele, profil, valeurs, self._reference)[0])
        effets = effets_champs(self._modele, profil, self._reference)
        prediction = Prediction(probabilite, valeurs, len(self._variables),
                                self.precision_attendue(valeurs), effets)
        if enregistrer:
            self.enregistrer(prediction)
        return prediction

    def enregistrer(self, prediction: Prediction) -> None:
        """Ajoute la prédiction à l'historique.

        Laisse passer OSError (ex. fichier ouvert dans Excel) pour que l'interface l'affiche.
        """
        self._historique.ajouter(prediction.vers_ligne())

    def scores_test(self) -> tuple[np.ndarray, np.ndarray]:
        """Renvoie (risques prédits, départs réels) pour les employés du jeu de test."""
        if self._scores_test is None:
            self._scores_test = self._modele.probabilites_depart(self._X_test)
        return self._scores_test.copy(), self._y_test.copy()

    def exemple(self, genre: str) -> tuple[dict[str, str], bool]:
        """Renvoie les saisies d'un vrai employé du test et s'il est réellement parti.

        genre : « risque » (le départ le mieux détecté), « stable » (le maintien le plus sûr)
        ou « hasard ». Lève ValueError pour un autre genre.
        """
        scores, departs = self.scores_test()
        if genre == "risque":
            candidats = np.flatnonzero(departs == 1)
            indice = candidats[np.argmax(scores[candidats])]
        elif genre == "stable":
            candidats = np.flatnonzero(departs == 0)
            indice = candidats[np.argmin(scores[candidats])]
        elif genre == "hasard":
            indice = int(self._generateur.integers(len(departs)))
        else:
            raise ValueError(f"Genre d'exemple inconnu : {genre}")
        ligne = self._X_test.iloc[indice]
        saisies = {nom: variable.formater(ligne[nom]) for nom, variable in self._variables.items()}
        return saisies, bool(departs[indice])

    def __repr__(self) -> str:
        return f"Application(modele={self._modele.nom!r}, variables={len(self._variables)})"
