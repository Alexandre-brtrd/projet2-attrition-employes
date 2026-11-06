"""Test de bout en bout : entraînement, fichiers produits, puis application rechargée depuis le disque."""

import os
import sys

import pytest

import main as module_main
from frontend.application import Application
from backend.config import CHEMIN_CSV, NOM_JEU_TEST, NOM_METADONNEES, NOM_MODELE, NOM_REFERENCE
from backend.entrainement import entrainer_et_sauvegarder, resume_entrainement
from backend.exceptions import FichierIntrouvableError


@pytest.fixture(scope="module")
def entrainement(tmp_path_factory):
    """Entraîne une fois dans un dossier temporaire (2 tirages seulement pour aller vite)."""
    dossier = tmp_path_factory.mktemp("entrainement")
    metadonnees = entrainer_et_sauvegarder(CHEMIN_CSV, str(dossier / "modeles"), str(dossier / "figures"),
                                           nb_tirages=2)
    return dossier, metadonnees


def test_fichiers_produits(entrainement):
    dossier, _ = entrainement
    for nom in (NOM_MODELE, NOM_METADONNEES, NOM_JEU_TEST, NOM_REFERENCE):
        assert os.path.exists(dossier / "modeles" / nom)
    assert len(os.listdir(dossier / "figures")) == 5


def test_le_modele_retenu_bat_la_reference(entrainement):
    _, metadonnees = entrainement
    metriques = metadonnees["metriques_test"]
    retenu = metriques[metadonnees["modele"]]["exactitude_equilibree"]
    assert retenu > metriques["Référence (classe majoritaire)"]["exactitude_equilibree"] + 0.15


def test_la_satisfaction_n_est_pas_previsible(entrainement):
    _, metadonnees = entrainement
    assert metadonnees["comparaison_cibles"]["Satisfaction (≥ 3 sur 4)"]["Régression logistique"] < 0.55


def test_courbe_de_precision_complete(entrainement):
    _, metadonnees = entrainement
    courbe = metadonnees["courbe_precision"]
    assert len(courbe["nb_champs"]) == len(metadonnees["colonnes"]) + 1
    assert courbe["ordre_importance"][0] == pytest.approx(0.5)


def test_application_rechargee_depuis_les_fichiers(entrainement, tmp_path):
    dossier, _ = entrainement
    application = Application.depuis_fichiers(str(dossier / "modeles"), str(tmp_path / "historique.csv"))
    prediction = application.predire({"OverTime": "Oui", "Age": "25"})
    assert 0 <= prediction.probabilite <= 1
    assert len(application.historique) == 1


def test_resume_lisible(entrainement):
    _, metadonnees = entrainement
    assert "Régression logistique" in resume_entrainement(metadonnees)


def test_application_sans_modele(tmp_path):
    with pytest.raises(FichierIntrouvableError, match="entrainer"):
        Application.depuis_fichiers(str(tmp_path), str(tmp_path / "historique.csv"))


def test_main_signale_une_erreur_sans_planter(monkeypatch, capsys):
    def entrainement_impossible():
        raise FichierIntrouvableError("donnees/absent.csv")
    monkeypatch.setattr(module_main, "entrainer_et_sauvegarder", entrainement_impossible)
    assert module_main.main(["entrainer"]) == 1
    assert "Fichier introuvable" in capsys.readouterr().err


def test_main_explique_comment_installer_une_bibliotheque_manquante(monkeypatch, capsys):
    # Une entrée None dans sys.modules fait échouer l'import comme une bibliothèque absente.
    monkeypatch.setitem(sys.modules, "frontend.fenetre", None)
    assert module_main.main([]) == 1
    erreur = capsys.readouterr().err
    assert "frontend.fenetre" in erreur
    assert "pip install -r" in erreur
