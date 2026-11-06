"""Graphiques propres à l'interface : précision selon les champs, facteurs, sens du risque.

Chaque graphique répond à une question que se pose l'utilisateur ; son titre est cette
question ou sa réponse. Thème sombre par défaut ; l'interface passe theme="clair" en mode clair.
"""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from backend.style import couleurs, habiller, legende, libelle_court, nouvelle_figure

FORMAT_POURCENT = FuncFormatter(lambda valeur, _: f"{valeur:.0f} %")


def figure_precision_champs(courbe: dict, nb_champs: int | None = None, precision: float | None = None,
                            theme: str = "sombre", premier_champ: str | None = None) -> Figure:
    """Précision attendue selon le nombre de champs renseignés, avec la position de l'utilisateur.

    courbe : dictionnaire « courbe_precision » des métadonnées ; premier_champ : libellé du
    champ le plus utile, annoté sur la courbe.
    """
    palette = couleurs(theme)
    bleu, orange = palette["series"][0], palette["series"][1]
    figure = nouvelle_figure(theme)
    axe = figure.add_subplot()
    x = np.asarray(courbe["nb_champs"])
    utiles = np.asarray(courbe["ordre_importance"]) * 100
    axe.axhspan(40, 50, color=palette["neutre"], alpha=0.35, linewidth=0)
    # Les annotations ne comptent pas dans la mise en page (in_layout=False) : dans une petite
    # fenêtre, elles ne doivent pas écraser la zone du graphique.
    axe.text(0.98, 5 / 45, "Zone du hasard (pas mieux qu'une pièce de monnaie)", transform=axe.transAxes,
             ha="right", va="center", fontsize=8, color=palette["encre_secondaire"], in_layout=False)
    axe.fill_between(x, np.asarray(courbe["aleatoire_bas"]) * 100, np.asarray(courbe["aleatoire_haut"]) * 100,
                     color=orange, alpha=0.15, linewidth=0)
    axe.plot(x, np.asarray(courbe["aleatoire_moyenne"]) * 100, color=orange, linewidth=2,
             label="Champs remplis au hasard (bande : 8 essais sur 10)")
    axe.plot(x, utiles, color=bleu, linewidth=2.2, label="Champs les plus utiles remplis d'abord")
    if premier_champ and len(x) > 1:
        axe.annotate(f"« {premier_champ} » seul : {utiles[1]:.0f} %", (x[1], utiles[1]), xytext=(14, 18),
                     textcoords="offset points", fontsize=8, color=palette["encre_secondaire"], in_layout=False,
                     arrowprops={"arrowstyle": "-", "color": palette["encre_discrete"], "linewidth": 0.8})
    if nb_champs is not None and precision is not None:
        axe.plot([nb_champs], [precision * 100], marker="o", markersize=11, color=palette["encre"],
                 markeredgecolor=palette["surface"], markeredgewidth=2.5, linestyle="none", label="Votre saisie")
        vers_gauche = nb_champs > x[-1] * 0.6
        axe.annotate(f"Vous : {nb_champs} champ(s) → {precision * 100:.0f} %", (nb_champs, precision * 100),
                     xytext=(-10 if vers_gauche else 10, 12), textcoords="offset points", fontsize=9,
                     fontweight="bold", color=palette["encre"], ha="right" if vers_gauche else "left",
                     in_layout=False)
    axe.set_xlim(0, x[-1])
    axe.set_ylim(40, 85)
    axe.yaxis.set_major_formatter(FORMAT_POURCENT)
    habiller(axe, theme, "Plus vous renseignez de champs, plus c'est fiable",
             "Nombre de champs remplis", "Précision attendue")
    legende(axe, theme, loc="upper left")
    return figure


def figure_effets(effets: dict[str, float], valeurs_affichees: dict[str, str] | None = None, nb: int = 8,
                  message_vide: str = "Aucun champ renseigné", theme: str = "sombre") -> Figure:
    """Barres horizontales : de combien chaque information saisie fait monter ou baisser le risque.

    effets : {nom : effet entre -1 et 1} ; valeurs_affichees : {nom : valeur saisie, en texte}.
    """
    palette = couleurs(theme)
    hausse, baisse = palette["rouge"], palette["vert"]
    valeurs_affichees = valeurs_affichees or {}
    figure = nouvelle_figure(theme)
    axe = figure.add_subplot()
    principaux = sorted(effets.items(), key=lambda paire: abs(paire[1]), reverse=True)[:nb]
    principaux.reverse()
    habiller(axe, theme, "Ce qui pèse dans ce résultat",
             "Écart de risque si l'on retirait cette information (points de %)", "")
    if not principaux:
        axe.text(0.5, 0.5, message_vide, ha="center", va="center", transform=axe.transAxes,
                 color=palette["encre_secondaire"])
        axe.set_axis_off()
        return figure
    valeurs = [effet * 100 for _, effet in principaux]
    etiquettes = [f"{libelle_court(nom)} = {valeurs_affichees[nom]}" if nom in valeurs_affichees
                  else libelle_court(nom) for nom, _ in principaux]
    barres = axe.barh(etiquettes, valeurs, height=0.6,
                      color=[hausse if valeur > 0 else baisse for valeur in valeurs])
    axe.bar_label(barres, labels=[f"{valeur:+.0f}" if round(valeur) else "≈ 0" for valeur in valeurs],
                  padding=3, fontsize=8, color=palette["encre_secondaire"])
    limite = max(max(abs(valeur) for valeur in valeurs) * 1.35, 5)
    axe.set_xlim(-limite, limite)
    axe.axvline(0, color=palette["axe"], linewidth=1)
    axe.text(0.02, 1.0, "← fait baisser le risque", transform=axe.transAxes, ha="left", va="bottom",
             fontsize=8, color=baisse)
    axe.text(0.98, 1.0, "fait monter le risque →", transform=axe.transAxes, ha="right", va="bottom",
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
        # Au-dessus de l'étiquette « n sur m » de la barre, sans flèche pour ne pas la couvrir.
        axe.annotate(f"Votre employé ({probabilite * 100:.0f} %)", (choisie, taux[choisie]),
                     xytext=(0, 20), textcoords="offset points", ha="center", va="bottom", fontsize=9,
                     fontweight="bold", color=palette["encre"], in_layout=False)
    axe.set_xticks(positions, [f"{tranche['bas'] * 100:.0f}–{tranche['haut'] * 100:.0f} %" for tranche in tranches])
    axe.set_ylim(0, 100)
    axe.yaxis.set_major_formatter(FORMAT_POURCENT)
    habiller(axe, theme, "Parmi les employés au risque semblable, combien sont vraiment partis ?",
             "Risque estimé par le modèle (avec les mêmes champs remplis que vous)", "Réellement partis")
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
