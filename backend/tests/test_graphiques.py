"""Tests rapides des graphiques du modèle, dans les deux thèmes."""

import pytest
from matplotlib.colors import to_hex
from matplotlib.figure import Figure

from backend.graphiques import (figure_comparaison_cibles, figure_importances,
                                            figure_matrice_confusion, figure_satisfaction, figure_taux_depart)
from backend.style import THEMES, couleurs


def _titre(figure: Figure) -> str:
    return figure.axes[0].get_title(loc="left")


def test_graphiques_d_exploration(jeu):
    assert isinstance(figure_taux_depart(jeu.tableau), Figure)
    assert "satisfaits" in _titre(figure_satisfaction(jeu.tableau))


def test_graphiques_d_evaluation():
    matrice = figure_matrice_confusion([[254, 55], [22, 37]])
    assert _titre(matrice) == "Matrice de confusion : 291 employés de test sur 368 bien classés"
    assert "fausses alertes\n(18 % des restés)" in [texte.get_text() for texte in matrice.axes[0].texts]
    assert _titre(figure_importances({"OverTime": 0.07, "Age": 0.02})) == "Variables les plus utiles au modèle"
    comparaison = {"Satisfaction": {"Référence": 0.5, "Logistique": 0.44},
                   "Départ": {"Référence": 0.5, "Logistique": 0.72}}
    assert len(figure_comparaison_cibles(comparaison).axes[0].patches) == 4


@pytest.mark.parametrize("theme", list(THEMES))
def test_le_fond_suit_le_theme(theme):
    figure = figure_matrice_confusion([[1, 2], [3, 4]], theme=theme)
    assert to_hex(figure.get_facecolor()) == couleurs(theme)["surface"]


def test_theme_inconnu():
    with pytest.raises(ValueError, match="Thème inconnu"):
        couleurs("rose")
