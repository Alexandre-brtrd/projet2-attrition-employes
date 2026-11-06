"""Tests des modèles : entraînement, prédiction, évaluation et sauvegarde."""

import joblib
import numpy as np
import pytest

from backend.entrainement import colonnes_par_encodage
from backend.exceptions import DonneeInvalideError, FichierIntrouvableError, ModeleNonEntraineError
from backend.modeles import Modele, ModeleForetAleatoire, ModeleLogistique, ModeleReference


@pytest.fixture(scope="module")
def colonnes(variables):
    return colonnes_par_encodage(variables)


def test_prediction_avant_entrainement(colonnes, separation):
    with pytest.raises(ModeleNonEntraineError):
        ModeleLogistique(*colonnes).probabilites_depart(separation[1])


def test_la_reference_predit_toujours_reste(colonnes, separation):
    X_entr, X_test, y_entr, y_test = separation
    reference = ModeleReference(*colonnes).entrainer(X_entr, y_entr)
    assert set(reference.predire(X_test)) == {0}
    assert reference.evaluer(X_test, y_test)["exactitude_equilibree"] == pytest.approx(0.5)


def test_la_logistique_bat_la_reference(modele_logistique, separation):
    resultats = modele_logistique.evaluer(separation[1], separation[3])
    assert resultats["exactitude_equilibree"] > 0.65
    assert resultats["auc"] > 0.75


def test_probabilites_entre_0_et_1(modele_logistique, separation):
    probabilites = modele_logistique.probabilites_depart(separation[1])
    assert probabilites.shape == (len(separation[1]),)
    assert np.all((probabilites >= 0) & (probabilites <= 1))


def test_seuil_de_decision(modele_logistique, separation):
    X_test = separation[1]
    assert modele_logistique.predire(X_test, seuil=0.0).sum() == len(X_test)
    assert modele_logistique.predire(X_test, seuil=1.01).sum() == 0


def test_colonne_manquante(modele_logistique, separation):
    with pytest.raises(DonneeInvalideError, match="Age"):
        modele_logistique.probabilites_depart(separation[1].drop(columns=["Age"]))


def test_tailles_differentes_a_l_entrainement(colonnes, separation):
    X_entr, _, y_entr, _ = separation
    with pytest.raises(DonneeInvalideError, match="lignes"):
        ModeleLogistique(*colonnes).entrainer(X_entr, y_entr.iloc[:10])


def test_le_decorateur_mesure_la_duree(modele_logistique):
    assert modele_logistique.durees["entrainer"] > 0


def test_validation_croisee_de_la_reference(colonnes, separation):
    X_entr, _, y_entr, _ = separation
    assert ModeleReference(*colonnes).validation_croisee(X_entr, y_entr) == pytest.approx(0.5)


def test_foret_reproductible_avec_la_meme_graine(colonnes, separation):
    X_entr, X_test, y_entr, _ = separation
    premiere = ModeleForetAleatoire(*colonnes, graine=7).entrainer(X_entr, y_entr)
    seconde = ModeleForetAleatoire(*colonnes, graine=7).entrainer(X_entr, y_entr)
    assert premiere.probabilites_depart(X_test) == pytest.approx(seconde.probabilites_depart(X_test))


def test_sauvegarde_puis_rechargement(tmp_path, modele_logistique, separation):
    chemin = str(tmp_path / "modele.joblib")
    modele_logistique.sauvegarder(chemin)
    recharge = Modele.charger(chemin)
    assert isinstance(recharge, ModeleLogistique)
    assert recharge.probabilites_depart(separation[1]) == pytest.approx(
        modele_logistique.probabilites_depart(separation[1]))


def test_sauvegarder_un_modele_non_entraine(tmp_path, colonnes):
    with pytest.raises(ModeleNonEntraineError):
        ModeleLogistique(*colonnes).sauvegarder(str(tmp_path / "modele.joblib"))


def test_charger_un_fichier_absent(tmp_path):
    with pytest.raises(FichierIntrouvableError):
        Modele.charger(str(tmp_path / "absent.joblib"))


def test_charger_un_fichier_qui_n_est_pas_un_modele(tmp_path):
    chemin = str(tmp_path / "autre.joblib")
    joblib.dump({"pas": "un modèle"}, chemin)
    with pytest.raises(DonneeInvalideError, match="ne contient pas"):
        Modele.charger(chemin)


def test_charger_un_fichier_illisible(tmp_path):
    chemin = tmp_path / "abime.joblib"
    chemin.write_bytes(b"ceci n'est pas un fichier joblib")
    with pytest.raises(DonneeInvalideError, match="autre version"):
        Modele.charger(str(chemin))


def test_str_et_repr(modele_logistique, colonnes):
    assert str(modele_logistique) == "Régression logistique (entraîné, 26 variables)"
    assert repr(ModeleReference(*colonnes)) == "ModeleReference(colonnes=26, entraine=False)"
