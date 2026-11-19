"""Graphiques propres à l'interface : facteurs du résultat et sens du risque affiché.

Chaque graphique répond à une question que se pose l'utilisateur ; son titre est cette
question ou sa réponse. Thème sombre par défaut ; l'interface passe theme="clair" en mode clair.
"""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from backend.style import couleurs, habiller, legende, libelle_court, nouvelle_figure

FORMAT_POURCENT = FuncFormatter(lambda valeur, _: f"{valeur:.0f} %")
NB_EFFETS = 8  # nombre maximal de barres du graphique des facteurs


def figure_effets(effets: dict[str, float], valeurs_affichees: dict[str, str], theme: str = "sombre") -> Figure:
    """Barres horizontales : de combien chaque information saisie fait monter ou baisser le risque.

    effets : {nom : effet entre -1 et 1}, au moins un champ ; valeurs_affichees : {nom : valeur saisie, en texte}.
    """
    palette = couleurs(theme)
    hausse, baisse = palette["rouge"], palette["vert"]
    figure = nouvelle_figure(theme)
    axe = figure.add_subplot()
    principaux = sorted(effets.items(), key=lambda paire: abs(paire[1]), reverse=True)[:NB_EFFETS]
    principaux.reverse()
    habiller(axe, theme, "", "Écart de risque (points de %)", "")
    # Titre aligné sur le bord de la figure : les longues étiquettes poussent l'axe vers la droite.
    figure.suptitle("Ce qui pèse dans ce résultat", x=0.02, ha="left", fontsize=11, color=palette["encre"])
    valeurs = [effet * 100 for _, effet in principaux]
    etiquettes = [f"{libelle_court(nom)} = {valeurs_affichees[nom]}" for nom, _ in principaux]
    barres = axe.barh(etiquettes, valeurs, height=0.6,
                      color=[hausse if valeur > 0 else baisse for valeur in valeurs])
    axe.bar_label(barres, labels=[f"{valeur:+.0f}" if round(valeur) else "≈ 0" for valeur in valeurs],
                  padding=3, fontsize=8, color=palette["encre_secondaire"])
    limite = max(max(abs(valeur) for valeur in valeurs) * 1.35, 5)
    axe.set_xlim(-limite, limite)
    axe.axvline(0, color=palette["axe"], linewidth=1)
    axe.text(0.02, 1.01, "← fait baisser", transform=axe.transAxes, ha="left", va="bottom",
             fontsize=8, color=baisse)
    axe.text(0.98, 1.01, "fait monter →", transform=axe.transAxes, ha="right", va="bottom",
             fontsize=8, color=hausse)
    axe.grid(axis="y", visible=False)
    return figure


def figure_risque_reel(tranches: list[dict], probabilite: float | None = None, theme: str = "sombre") -> Figure:
    """Ce que veut dire le risque affiché : part d'employés du test réellement partis, par tranche de risque.

    tranches : résultat de Application.tranches_de_risque ; probabilite : risque de l'employé saisi,
    dont la tranche est mise en évidence.
    """
    palette = couleurs(theme)
    figure = nouvelle_figure(theme)
    axe = figure.add_subplot()
    positions = np.arange(len(tranches))
    employes = np.array([tranche["employes"] for tranche in tranches])
    partis = np.array([tranche["partis"] for tranche in tranches])
    taux = np.divide(partis, employes, out=np.zeros(len(tranches)), where=employes > 0) * 100
    choisie = None
    if probabilite is not None:
        choisie = next(rang for rang, tranche in enumerate(tranches)
                       if probabilite < tranche["haut"] or rang == len(tranches) - 1)
    couleurs_barres = [palette["series"][0] if rang == choisie or choisie is None else palette["neutre"]
                       for rang in positions]
    barres = axe.bar(positions, taux, width=0.7, color=couleurs_barres)
    axe.bar_label(barres, labels=[f"{p} sur {e}" if e else "aucun" for p, e in zip(partis, employes)],
                  padding=3, fontsize=8, color=palette["encre_secondaire"])
    moyenne = partis.sum() / max(employes.sum(), 1) * 100
    axe.axhline(moyenne, color=palette["encre_discrete"], linestyle=":", linewidth=1.2,
                label=f"Moyenne de tous les employés du test ({moyenne:.0f} %)")
    legende(axe, theme, loc="upper left")
    if choisie is not None:
        # Au-dessus de l'étiquette « n sur m » de la barre, sans flèche pour ne pas la couvrir ;
        # aux extrémités, le texte part vers l'intérieur pour ne pas sortir de la figure.
        alignement = "left" if choisie == 0 else "right" if choisie == len(tranches) - 1 else "center"
        axe.annotate(f"Votre employé ({probabilite * 100:.0f} %)", (choisie, taux[choisie]),
                     xytext=(0, 20), textcoords="offset points", ha=alignement, va="bottom", fontsize=9,
                     fontweight="bold", color=palette["encre"], in_layout=False)
    axe.set_xticks(positions, [f"{tranche['bas'] * 100:.0f}–{tranche['haut'] * 100:.0f} %" for tranche in tranches])
    axe.set_ylim(0, 100)
    axe.yaxis.set_major_formatter(FORMAT_POURCENT)
    habiller(axe, theme, "Au même score, combien sont vraiment partis ?",
             "Score de risque (avec les mêmes champs que vous)", "Réellement partis")
    axe.grid(axis="x", visible=False)
    return figure


def figure_vide(message: str, theme: str = "sombre") -> Figure:
    """Figure sans axes qui affiche seulement un message (ex. « cliquez sur Prédire »)."""
    palette = couleurs(theme)
    figure = nouvelle_figure(theme)
    axe = figure.add_subplot()
    axe.set_facecolor(palette["surface"])
    axe.text(0.5, 0.5, message, ha="center", va="center", transform=axe.transAxes, fontsize=10,
             color=palette["encre_secondaire"], wrap=True)
    axe.set_axis_off()
    return figure
