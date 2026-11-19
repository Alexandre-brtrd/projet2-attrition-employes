"""Entraînement complet : exploration, comparaison des modèles, sauvegarde du modèle retenu.

Lancé par « python main.py entrainer ». Produit, dans backend/sauvegarde/ : le modèle (joblib),
les métadonnées (JSON), le jeu de test et les employés de référence (CSV) ;
dans backend/figures/ : les graphiques.
"""

import os
from datetime import datetime

from matplotlib.figure import Figure
from sklearn.model_selection import train_test_split

from backend.metriques import matrice_confusion
from backend.modeles import ModeleLogistique, ModeleReference
from backend.saisie_partielle import courbe_precision, courbe_precision_aleatoire
from backend.config import (CHEMIN_CSV, COLONNE_CIBLE, DESCRIPTIONS, DOSSIER_FIGURES, DOSSIER_SAUVEGARDE,
                          GRAINE, NB_TIRAGES_COURBE, NOM_JEU_TEST, NOM_METADONNEES, NOM_MODELE,
                          NOM_REFERENCE, PROPORTION_TEST, SEUIL_DECISION, TAILLE_REFERENCE,
                          VALEUR_DEPART)
from backend.jeu_de_donnees import JeuDeDonnees, creer_variables, ecrire_json
from backend.variables import Variable
from backend.graphiques import (figure_comparaison_cibles, figure_importances,
                                            figure_matrice_confusion, figure_satisfaction, figure_taux_depart)
from backend.style import couleurs


def colonnes_par_encodage(variables: list[Variable]) -> tuple[list[str], list[str]]:
    """Sépare les noms de variables en (numériques ou ordinales, catégorielles)."""
    numeriques = [variable.nom for variable in variables if variable.encodage == "numerique"]
    categorielles = [variable.nom for variable in variables if variable.encodage == "categoriel"]
    return numeriques, categorielles


def analyser_satisfaction(jeu: JeuDeDonnees, graine: int = GRAINE) -> dict[str, float]:
    """Tente de prédire la satisfaction au travail (niveau 3 ou 4 sur 4) à partir des autres variables.

    Renvoie l'exactitude équilibrée sur le test de la référence et de la régression logistique.
    Cette analyse justifie le choix de la cible « départ » (voir DECISIONS.md).
    """
    X = jeu.caracteristiques.drop(columns=["JobSatisfaction"])
    y = (jeu.tableau["JobSatisfaction"] >= 3).astype(int)
    X_entr, X_test, y_entr, y_test = train_test_split(X, y, test_size=PROPORTION_TEST,
                                                      random_state=graine, stratify=y)
    numeriques = [nom for nom, description in DESCRIPTIONS.items()
                  if description["type"] != "categorielle" and nom != "JobSatisfaction"]
    categorielles = [nom for nom, description in DESCRIPTIONS.items()
                     if description["type"] == "categorielle"]
    resultats = {}
    for classe in (ModeleReference, ModeleLogistique):
        modele = classe(numeriques, categorielles, graine).entrainer(X_entr, y_entr)
        resultats[modele.nom] = modele.evaluer(X_test, y_test)["exactitude_equilibree"]
    return resultats


def _enregistrer_figure(figure: Figure, dossier: str, nom_fichier: str) -> None:
    """Enregistre une figure en PNG dans dossier (thème clair, pour le README et la présentation)."""
    figure.savefig(os.path.join(dossier, nom_fichier), dpi=150, facecolor=couleurs("clair")["surface"])


def entrainer_et_sauvegarder(chemin_csv: str = CHEMIN_CSV, dossier_sauvegarde: str = DOSSIER_SAUVEGARDE,
                             dossier_figures: str = DOSSIER_FIGURES,
                             nb_tirages: int = NB_TIRAGES_COURBE, graine: int = GRAINE) -> dict:
    """Exécute tout l'entraînement et renvoie les métadonnées enregistrées.

    Lève FichierIntrouvableError si le CSV est absent, DonneeInvalideError s'il est mal formé.
    """
    jeu = JeuDeDonnees(chemin_csv).charger()
    jeu.nettoyer()
    os.makedirs(dossier_figures, exist_ok=True)
    _enregistrer_figure(figure_taux_depart(jeu.tableau), dossier_figures, "exploration_taux_depart.png")
    _enregistrer_figure(figure_satisfaction(jeu.tableau), dossier_figures, "exploration_satisfaction.png")

    X_entr, X_test, y_entr, y_test = jeu.separer(PROPORTION_TEST, graine)
    variables = creer_variables(X_entr)
    numeriques, categorielles = colonnes_par_encodage(variables)
    # Deux modèles comparés : la référence (toujours « reste ») sert d'étalon, la régression
    # logistique est le seul modèle sauvegardé et utilisé par l'application.
    reference_triviale = ModeleReference(numeriques, categorielles, graine)
    retenu = ModeleLogistique(numeriques, categorielles, graine)
    metriques, validation = {}, {}
    for modele in (reference_triviale, retenu):
        # Validation croisée sur l'entraînement ; le test ne sert qu'à mesurer, une seule fois.
        validation[modele.nom] = modele.validation_croisee(X_entr, y_entr)
        modele.entrainer(X_entr, y_entr)
        metriques[modele.nom] = modele.evaluer(X_test, y_test)

    # Employés de référence : remplacent les champs vides (voir saisie_partielle.py).
    reference = X_entr.sample(n=TAILLE_REFERENCE, random_state=graine)
    importances = retenu.importances(X_entr, y_entr)
    ordre = sorted(importances, key=lambda nom: importances[nom], reverse=True)
    aleatoire = courbe_precision_aleatoire(retenu, X_test, y_test, reference, nb_tirages, graine)
    courbe = {
        "nb_champs": list(range(len(ordre) + 1)),
        "ordre": ordre,
        "ordre_importance": courbe_precision(retenu, X_test, y_test, reference, ordre),
        "aleatoire_moyenne": aleatoire["moyenne"],
        "aleatoire_bas": aleatoire["bas"],
        "aleatoire_haut": aleatoire["haut"],
    }
    matrice = matrice_confusion(y_test, retenu.predire(X_test))
    satisfaction = analyser_satisfaction(jeu, graine)
    comparaison = {"Satisfaction (≥ 3 sur 4)": satisfaction,
                   "Départ": {nom: metriques[nom]["exactitude_equilibree"] for nom in satisfaction}}

    _enregistrer_figure(figure_matrice_confusion(matrice), dossier_figures, "matrice_confusion.png")
    _enregistrer_figure(figure_importances(importances), dossier_figures, "importances.png")
    _enregistrer_figure(figure_comparaison_cibles(comparaison), dossier_figures, "comparaison_cibles.png")

    os.makedirs(dossier_sauvegarde, exist_ok=True)
    retenu.sauvegarder(os.path.join(dossier_sauvegarde, NOM_MODELE))
    with open(os.path.join(dossier_sauvegarde, NOM_JEU_TEST), "w", encoding="utf-8", newline="") as fichier:
        X_test.assign(Depart=y_test.to_numpy()).to_csv(fichier, index=False)
    with open(os.path.join(dossier_sauvegarde, NOM_REFERENCE), "w", encoding="utf-8", newline="") as fichier:
        reference.to_csv(fichier, index=False)
    metadonnees = {
        "date_entrainement": datetime.now().isoformat(timespec="seconds"),
        "source": "IBM HR Analytics Employee Attrition & Performance (Kaggle, ODbL / DbCL)",
        "cible": {"colonne": COLONNE_CIBLE, "valeur_positive": VALEUR_DEPART,
                  "description": "1 = l'employé a quitté l'entreprise, 0 = il est resté"},
        "modele": retenu.nom,
        "seuil_decision": SEUIL_DECISION,
        "duree_entrainement_s": retenu.durees["entrainer"],
        "lignes": {"total": len(jeu), "entrainement": len(X_entr), "test": len(X_test)},
        "taux_depart": jeu.taux_depart(),
        "nettoyage": jeu.rapport,
        "colonnes": retenu.colonnes,
        "variables": [variable.vers_dict() for variable in variables],
        "metriques_test": metriques,
        "validation_croisee": validation,
        "matrice_confusion": matrice.tolist(),
        "importances": importances,
        "courbe_precision": courbe,
        "comparaison_cibles": comparaison,
    }
    ecrire_json(os.path.join(dossier_sauvegarde, NOM_METADONNEES), metadonnees)
    return metadonnees


def resume_entrainement(metadonnees: dict) -> str:
    """Renvoie un résumé lisible de l'entraînement (affiché par main.py)."""
    lignes = ["Nettoyage :", *(f"  - {etape}" for etape in metadonnees["nettoyage"]), "",
              f"{'Modèle':34s}{'Exact. équil. (test)':>22s}{'Valid. croisée':>16s}{'AUC':>8s}"]
    for nom, resultats in metadonnees["metriques_test"].items():
        lignes.append(f"{nom:34s}{resultats['exactitude_equilibree']:>22.3f}"
                      f"{metadonnees['validation_croisee'][nom]:>16.3f}{resultats.get('auc', 0.5):>8.3f}")
    courbe = metadonnees["courbe_precision"]
    lignes += ["", f"Modèle retenu : {metadonnees['modele']} "
                   f"(entraîné en {metadonnees['duree_entrainement_s']:.2f} s)",
               f"Précision attendue avec 0 / 5 / tous les champs (les plus utiles d'abord) : "
               f"{courbe['ordre_importance'][0]:.3f} / {courbe['ordre_importance'][5]:.3f} / "
               f"{courbe['ordre_importance'][-1]:.3f}",
               "Prédire la satisfaction au lieu du départ : " + ", ".join(
                   f"{nom} {valeur:.3f}" for nom, valeur
                   in metadonnees["comparaison_cibles"]["Satisfaction (≥ 3 sur 4)"].items())]
    return "\n".join(lignes)
