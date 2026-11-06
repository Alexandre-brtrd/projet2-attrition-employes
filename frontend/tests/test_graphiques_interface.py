"""Tests rapides des graphiques de l'interface (thème sombre par défaut)."""

import pytest
from matplotlib.colors import to_hex
from matplotlib.figure import Figure

from frontend.graphiques import figure_effets, figure_precision_champs, figure_risque_reel, figure_vide
from backend.style import couleurs

COURBE = {"nb_champs": [0, 1, 2], "aleatoire_bas": [0.5, 0.5, 0.6], "aleatoire_haut": [0.5, 0.7, 0.7],
          "aleatoire_moyenne": [0.5, 0.6, 0.65], "ordre_importance": [0.5, 0.69, 0.7]}
TRANCHES = [{"bas": 0.0, "haut": 0.5, "employes": 10, "partis": 1},
            {"bas": 0.5, "haut": 1.0, "employes": 4, "partis": 3}]


def _textes(figure: Figure) -> str:
    return " ".join(texte.get_text() for texte in figure.axes[0].texts)


def test_courbe_de_precision_avec_la_saisie():
    figure = figure_precision_champs(COURBE, 1, 0.69, premier_champ="Heures supplémentaires")
    assert figure.axes[0].get_title(loc="left").startswith("Plus vous renseignez")
    assert to_hex(figure.get_facecolor()) == couleurs("sombre")["surface"]
    assert "Vous : 1 champ(s) → 69 %" in _textes(figure)
    assert "« Heures supplémentaires » seul : 69 %" in _textes(figure)


def test_effets_et_message_sans_donnees():
    figure = figure_effets({"OverTime": 0.2, "Age": -0.05}, {"OverTime": "Oui"})
    assert len(figure.axes[0].patches) == 2
    etiquettes = [etiquette.get_text() for etiquette in figure.axes[0].get_yticklabels()]
    assert "Heures supplémentaires = Oui" in etiquettes
    vide = figure_effets({}, message_vide="Rien à afficher")
    assert not vide.axes[0].axison


def test_risque_reel_met_en_evidence_la_tranche_de_l_employe():
    figure = figure_risque_reel(TRANCHES, 0.68, theme="clair")
    barres = figure.axes[0].patches
    assert [barre.get_height() for barre in barres] == pytest.approx([10, 75])
    palette = couleurs("clair")
    assert to_hex(barres[1].get_facecolor()) == palette["series"][0]
    assert to_hex(barres[0].get_facecolor()) == palette["neutre"]
    assert "Votre employé (68 %)" in _textes(figure)


def test_risque_reel_sans_prediction_et_tranche_vide():
    tranches = [*TRANCHES, {"bas": 1.0, "haut": 1.0, "employes": 0, "partis": 0}]
    figure = figure_risque_reel(tranches)
    assert figure.axes[0].patches[2].get_height() == 0
    # Un risque de 100 % tombe dans la dernière tranche sans erreur.
    assert isinstance(figure_risque_reel(TRANCHES, 1.0), Figure)


def test_figure_vide():
    assert not figure_vide("Cliquez sur Prédire").axes[0].axison
