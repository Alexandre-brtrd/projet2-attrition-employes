"""Couleurs et habillage communs à tous les graphiques.

Thème « clair » pour les figures enregistrées (README, présentation) et thème « sombre »
pour l'interface graphique. Les figures sont des objets Figure (sans pyplot).
"""

from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure

from backend.config import DESCRIPTIONS

# « surface » est aussi le fond des cartes de l'interface (frontend/theme.py, CARTE).
# « neutre » sert aux barres de contexte, « vert » et « rouge » aux bonnes et mauvaises réponses.
THEMES = {
    "clair": {
        "surface": "#ffffff", "encre": "#191c27", "encre_secondaire": "#4f5568",
        "encre_discrete": "#7d8396", "grille": "#eceef4", "axe": "#c9ccd8", "neutre": "#cfd2de",
        "series": ["#4353c4", "#e0702e", "#1f9b6e", "#8a5cd1"], "rouge": "#c4314b", "vert": "#1f8a4c",
        "sequentiel": ["#eef0fb", "#2f3d9e"],
    },
    "sombre": {
        "surface": "#1a1d26", "encre": "#e9eaf0", "encre_secondaire": "#a4a9ba",
        "encre_discrete": "#717789", "grille": "#272c39", "axe": "#3a4052", "neutre": "#3a4052",
        "series": ["#8392ff", "#f0894a", "#3cc497", "#b494f0"], "rouge": "#ff6b81", "vert": "#4cc17a",
        "sequentiel": ["#20242f", "#5563d6"],
    },
}


def couleurs(theme: str) -> dict:
    """Renvoie la palette du thème ; lève ValueError si le thème est inconnu."""
    if theme not in THEMES:
        raise ValueError(f"Thème inconnu : {theme!r} (choix : {', '.join(THEMES)})")
    return THEMES[theme]


def nouvelle_figure(theme: str, largeur: float = 6.4, hauteur: float = 4.2) -> Figure:
    """Renvoie une figure vide aux couleurs du thème."""
    return Figure(figsize=(largeur, hauteur), dpi=100, layout="constrained",
                  facecolor=couleurs(theme)["surface"])


def habiller(axe, theme: str, titre: str, etiquette_x: str, etiquette_y: str) -> None:
    """Applique titre, étiquettes d'axes et style discret (grille fine, pas de cadre)."""
    palette = couleurs(theme)
    axe.set_facecolor(palette["surface"])
    axe.set_title(titre, fontsize=11, color=palette["encre"], loc="left")
    axe.set_xlabel(etiquette_x, fontsize=9, color=palette["encre_secondaire"])
    axe.set_ylabel(etiquette_y, fontsize=9, color=palette["encre_secondaire"])
    axe.tick_params(colors=palette["encre_secondaire"], labelsize=8)
    axe.grid(True, color=palette["grille"], linewidth=0.8)
    axe.set_axisbelow(True)
    for cote in ("top", "right"):
        axe.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        axe.spines[cote].set_color(palette["axe"])


def legende(axe, theme: str, **options) -> None:
    """Légende sans cadre, au texte lisible dans les deux thèmes."""
    axe.legend(fontsize=8, frameon=False, labelcolor=couleurs(theme)["encre_secondaire"], **options)


def degrade(theme: str) -> LinearSegmentedColormap:
    """Dégradé d'une seule teinte (bleu), du plus faible au plus fort."""
    return LinearSegmentedColormap.from_list(f"bleus_{theme}", couleurs(theme)["sequentiel"])


def libelle(nom: str) -> str:
    """Libellé français d'une colonne (le nom brut si elle n'est pas décrite)."""
    return DESCRIPTIONS.get(nom, {}).get("libelle", nom)


def libelle_court(nom: str) -> str:
    """Libellé sans la précision entre parenthèses (« Âge (ans) » -> « Âge »), pour les axes."""
    return libelle(nom).split(" (")[0]


def texte_valeur(nom: str, valeur: object) -> str:
    """Traduction d'une valeur du jeu de données (« Yes » -> « Oui »)."""
    return str(DESCRIPTIONS.get(nom, {}).get("valeurs", {}).get(valeur, valeur))
