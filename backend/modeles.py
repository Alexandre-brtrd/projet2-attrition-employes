"""Modèles de classification du départ d'un employé.

Hiérarchie :
    Modele (abstraite)       prétraitement, entraînement, prédiction, évaluation, sauvegarde
    ├── ModeleReference      répond toujours la classe majoritaire (point de comparaison)
    ├── ModeleLogistique     régression logistique (modèle retenu)
    └── ModeleForetAleatoire forêt aléatoire (modèle comparé)
"""

import functools
import os
import pickle
import time
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.config import GRAINE, NB_PLIS_VALIDATION, SEUIL_DECISION
from backend.jeu_de_donnees import verifier_fichier
from backend.exceptions import DonneeInvalideError, ModeleNonEntraineError
from backend.metriques import resume_metriques


def chronometre(methode: Callable) -> Callable:
    """Décorateur : mesure la durée d'une méthode et la range dans self._durees[nom de la méthode]."""
    @functools.wraps(methode)
    def enveloppe(self, *args, **kwargs):
        debut = time.perf_counter()
        resultat = methode(self, *args, **kwargs)
        self._durees[methode.__name__] = time.perf_counter() - debut
        return resultat
    return enveloppe


class Modele(ABC):
    """Classe parente : un prétraitement commun suivi d'un estimateur scikit-learn."""

    nom = "Modèle"

    def __init__(self, colonnes_numeriques: list[str], colonnes_categorielles: list[str],
                 graine: int = GRAINE) -> None:
        """Reçoit les colonnes à standardiser, celles à encoder en indicatrices et la graine aléatoire."""
        self._colonnes_numeriques = list(colonnes_numeriques)
        self._colonnes_categorielles = list(colonnes_categorielles)
        self._graine = graine
        self._pipeline: Pipeline | None = None
        self._durees: dict[str, float] = {}

    @abstractmethod
    def _creer_estimateur(self) -> object:
        """Renvoie l'estimateur scikit-learn, non entraîné."""

    def _creer_pipeline(self) -> Pipeline:
        """Renvoie un pipeline neuf : standardisation des nombres, indicatrices des catégories, estimateur."""
        pretraitement = ColumnTransformer([
            ("nombres", StandardScaler(), self._colonnes_numeriques),
            ("categories", OneHotEncoder(handle_unknown="ignore"), self._colonnes_categorielles),
        ])
        return Pipeline([("pretraitement", pretraitement), ("estimateur", self._creer_estimateur())])

    @property
    def colonnes(self) -> list[str]:
        """Colonnes attendues en entrée, dans l'ordre utilisé par le modèle."""
        return self._colonnes_numeriques + self._colonnes_categorielles

    @property
    def est_entraine(self) -> bool:
        """Vrai une fois entrainer() appelé avec succès."""
        return self._pipeline is not None

    @property
    def durees(self) -> dict[str, float]:
        """Durées (en secondes) mesurées par le décorateur chronometre."""
        return dict(self._durees)

    def _verifier_colonnes(self, X: pd.DataFrame) -> None:
        """Lève DonneeInvalideError s'il manque des colonnes dans X."""
        manquantes = [nom for nom in self.colonnes if nom not in X.columns]
        if manquantes:
            raise DonneeInvalideError(f"Colonnes manquantes pour le modèle : {', '.join(manquantes)}")

    def _exiger_pipeline(self) -> Pipeline:
        """Renvoie le pipeline entraîné ; lève ModeleNonEntraineError sinon."""
        if self._pipeline is None:
            raise ModeleNonEntraineError(f"Le modèle « {self.nom} » n'est pas encore entraîné.")
        return self._pipeline

    @chronometre
    def entrainer(self, X: pd.DataFrame, y: pd.Series) -> "Modele":
        """Entraîne le modèle sur (X, y) et renvoie l'objet lui-même.

        Lève DonneeInvalideError si des colonnes manquent ou si X et y n'ont pas la même taille.
        """
        self._verifier_colonnes(X)
        if len(X) != len(y):
            raise DonneeInvalideError(f"X a {len(X)} lignes mais y en a {len(y)}.")
        pipeline = self._creer_pipeline()
        pipeline.fit(X[self.colonnes], y)
        self._pipeline = pipeline
        return self

    def probabilites_depart(self, X: pd.DataFrame) -> np.ndarray:
        """Renvoie, pour chaque ligne de X, le risque de départ entre 0 et 1.

        Lève ModeleNonEntraineError si le modèle n'est pas entraîné.
        """
        pipeline = self._exiger_pipeline()
        self._verifier_colonnes(X)
        probabilites = pipeline.predict_proba(X[self.colonnes])
        classes = list(pipeline.classes_)
        if 1 not in classes:
            return np.zeros(len(X))
        return probabilites[:, classes.index(1)]

    def predire(self, X: pd.DataFrame, seuil: float = SEUIL_DECISION) -> np.ndarray:
        """Renvoie 1 (départ) quand le risque atteint le seuil, 0 sinon."""
        return (self.probabilites_depart(X) >= seuil).astype(int)

    def evaluer(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """Renvoie les métriques de metriques.py, plus l'aire sous la courbe ROC si les deux classes sont présentes."""
        resultats = resume_metriques(y, self.predire(X))
        if len(np.unique(y)) == 2:
            resultats["auc"] = float(roc_auc_score(y, self.probabilites_depart(X)))
        return resultats

    def validation_croisee(self, X: pd.DataFrame, y: pd.Series,
                           nb_plis: int = NB_PLIS_VALIDATION) -> float:
        """Exactitude équilibrée moyenne en validation croisée stratifiée.

        À appeler sur l'ensemble d'entraînement seulement : le test reste intouché.
        """
        self._verifier_colonnes(X)
        plis = StratifiedKFold(n_splits=nb_plis, shuffle=True, random_state=self._graine)
        scores = cross_val_score(self._creer_pipeline(), X[self.colonnes], y, cv=plis,
                                 scoring="balanced_accuracy")
        return float(np.mean(scores))

    def importances(self, X: pd.DataFrame, y: pd.Series, nb_repetitions: int = 10) -> dict[str, float]:
        """Importance par permutation : baisse moyenne d'exactitude équilibrée quand on mélange une colonne."""
        resultat = permutation_importance(self._exiger_pipeline(), X[self.colonnes], y,
                                          scoring="balanced_accuracy", n_repeats=nb_repetitions,
                                          random_state=self._graine)
        return {nom: float(valeur) for nom, valeur in zip(self.colonnes, resultat.importances_mean)}

    def sauvegarder(self, chemin: str) -> None:
        """Enregistre le modèle entraîné avec joblib ; lève ModeleNonEntraineError s'il ne l'est pas."""
        self._exiger_pipeline()
        os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
        joblib.dump(self, chemin)

    @staticmethod
    def charger(chemin: str) -> "Modele":
        """Recharge un modèle enregistré par sauvegarder().

        Lève FichierIntrouvableError si le fichier est absent, DonneeInvalideError s'il est illisible,
        s'il a été créé avec une autre version de scikit-learn ou s'il ne contient pas un Modele.
        """
        verifier_fichier(chemin, "Lancez d'abord l'entraînement : python main.py entrainer")
        try:
            with warnings.catch_warnings():
                # Un modèle d'une autre version peut donner des résultats faux : on préfère réentraîner.
                warnings.simplefilter("error", InconsistentVersionWarning)
                modele = joblib.load(chemin)
        except (InconsistentVersionWarning, ImportError, AttributeError, EOFError, KeyError, TypeError,
                ValueError, pickle.UnpicklingError) as erreur:
            raise DonneeInvalideError(
                f"{os.path.basename(chemin)} a été créé avec une autre version des bibliothèques ou du code "
                f"({type(erreur).__name__}).") from None
        if not isinstance(modele, Modele):
            raise DonneeInvalideError(f"{chemin} ne contient pas un modèle du projet.")
        return modele

    def __str__(self) -> str:
        etat = "entraîné" if self.est_entraine else "non entraîné"
        return f"{self.nom} ({etat}, {len(self.colonnes)} variables)"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(colonnes={len(self.colonnes)}, entraine={self.est_entraine})"


class ModeleReference(Modele):
    """Référence triviale : prédit toujours la classe la plus fréquente (« reste »)."""

    nom = "Référence (classe majoritaire)"

    def _creer_estimateur(self) -> DummyClassifier:
        return DummyClassifier(strategy="most_frequent")


class ModeleLogistique(Modele):
    """Régression logistique ; les classes sont pondérées pour compenser les 16 % de départs."""

    nom = "Régression logistique"

    def _creer_estimateur(self) -> LogisticRegression:
        return LogisticRegression(class_weight="balanced", max_iter=1000)


class ModeleForetAleatoire(Modele):
    """Forêt de 300 arbres ; min_samples_leaf limite le surapprentissage sur 1100 employés."""

    nom = "Forêt aléatoire"

    def _creer_estimateur(self) -> RandomForestClassifier:
        return RandomForestClassifier(n_estimators=300, min_samples_leaf=5,
                                      class_weight="balanced", random_state=self._graine)

