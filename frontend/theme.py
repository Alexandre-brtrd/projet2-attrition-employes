"""Palette (thème clair et thème sombre) et polices de l'interface.

Chaque couleur est une paire (clair, sombre) : CustomTkinter choisit lui-même selon le
mode actif. Les tableaux ttk et les graphiques Matplotlib ne savent pas lire ces paires :
couleur() renvoie la bonne moitié. Le fond des cartes (CARTE) est celui des graphiques
(backend/style.py), pour que les figures se fondent dans la fenêtre.

La palette part d'un gris ardoise légèrement bleuté et d'un accent pervenche ; les couleurs
de risque (vert, ambre, orange, rouge) en sont indépendantes.
"""

from tkinter import ttk

import customtkinter as ctk

POLICE = "Segoe UI"

Paire = tuple[str, str]

FOND: Paire = ("#f3f4f8", "#12141b")
BARRE_LATERALE: Paire = ("#e9ebf2", "#0c0e13")
CARTE: Paire = ("#ffffff", "#1a1d26")
CARTE_RELIEF: Paire = ("#f4f5f9", "#20242f")
SAISIE: Paire = ("#f7f8fb", "#12141b")
BORDURE: Paire = ("#d9dce6", "#2d3240")
SURVOL: Paire = ("#e6e9f2", "#272c39")
TEXTE: Paire = ("#191c27", "#e9eaf0")
TEXTE_SECONDAIRE: Paire = ("#4f5568", "#a4a9ba")
TEXTE_DISCRET: Paire = ("#7d8396", "#717789")
ACCENT: Paire = ("#4353c4", "#8392ff")
ACCENT_SURVOL: Paire = ("#3443ab", "#6f7ff0")
ACCENT_DOUX: Paire = ("#e3e6fa", "#252a48")
TEXTE_SUR_ACCENT: Paire = ("#ffffff", "#10121a")
SUCCES: Paire = ("#1f8a4c", "#4cc17a")
ERREUR: Paire = ("#c4314b", "#ff6b81")
ERREUR_FOND: Paire = ("#fbe9ec", "#33181f")
AVERTISSEMENT: Paire = ("#8a5b00", "#e8b54a")
AVERTISSEMENT_FOND: Paire = ("#fff3d9", "#2a2416")

# Niveau de risque -> (couleur du texte et de la barre, fond du badge).
NIVEAUX: dict[str, tuple[Paire, Paire]] = {
    "faible": (("#1f8a4c", "#4cc17a"), ("#e5f5ec", "#15281d")),
    "modéré": (("#9a6a00", "#e0b043"), ("#fff1d1", "#2b2410")),
    "élevé": (("#c45a12", "#f39250"), ("#fde9da", "#2e1d11")),
    "très élevé": (("#c4314b", "#ff6b81"), ("#fbe9ec", "#33181f")),
}


def mode_sombre() -> bool:
    """Vrai si l'interface est actuellement en thème sombre."""
    return ctk.get_appearance_mode() == "Dark"


def couleur(paire: Paire) -> str:
    """Moitié de la paire qui correspond au thème actif (pour ttk et Matplotlib)."""
    return paire[1] if mode_sombre() else paire[0]


def theme_graphique() -> str:
    """Nom du thème des graphiques (backend/style.py) qui correspond au thème actif."""
    return "sombre" if mode_sombre() else "clair"


def basculer_theme() -> None:
    """Passe du thème clair au thème sombre, ou l'inverse."""
    ctk.set_appearance_mode("light" if mode_sombre() else "dark")


def police(taille: int = 13, gras: bool = False) -> ctk.CTkFont:
    """Police de l'interface (taille en pixels avant mise à l'échelle de l'écran)."""
    return ctk.CTkFont(family=POLICE, size=taille, weight="bold" if gras else "normal")


def configurer_tableaux(racine: ctk.CTk, echelle: float) -> None:
    """Style des tableaux ttk.Treeview (CustomTkinter n'a pas de tableau), à refaire à chaque
    changement de thème."""
    carte, relief = couleur(CARTE), couleur(CARTE_RELIEF)
    style = ttk.Style(racine)
    style.theme_use("clam")
    style.configure("Theme.Treeview", background=carte, fieldbackground=carte, foreground=couleur(TEXTE),
                    bordercolor=carte, lightcolor=carte, darkcolor=carte, borderwidth=0,
                    rowheight=int(34 * echelle), font=(POLICE, 10))
    style.configure("Theme.Treeview.Heading", background=relief, foreground=couleur(TEXTE_SECONDAIRE),
                    bordercolor=relief, lightcolor=relief, darkcolor=relief,
                    relief="flat", font=(POLICE, 10, "bold"), padding=(8, 8))
    style.map("Theme.Treeview", background=[("selected", couleur(ACCENT_DOUX))],
              foreground=[("selected", couleur(TEXTE))])
    style.map("Theme.Treeview.Heading", background=[("active", couleur(SURVOL))])
    style.layout("Theme.Treeview", [("Theme.Treeview.treearea", {"sticky": "nswe"})])
