"""Composants réutilisables de l'interface : cartes, tuiles, boutons, bulles d'aide, champs,
zone de graphique, schéma en boîtes et flèches."""

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from frontend.application import choix_en_boutons
from frontend.theme import (ACCENT, ACCENT_DOUX, ACCENT_SURVOL, BORDURE, CARTE, CARTE_RELIEF, ERREUR,
                            ERREUR_FOND, POLICE, SAISIE, SUCCES, SURVOL, TEXTE, TEXTE_DISCRET, TEXTE_SECONDAIRE,
                            TEXTE_SUR_ACCENT, couleur, police)
from backend.exceptions import DonneeInvalideError
from backend.variables import NON_RENSEIGNE, Variable, VariableCategorielle, VariableNumerique

LARGEUR_SAISIE = 250


def est_dans(widget: tk.Misc | None, conteneur: tk.Misc) -> bool:
    """Vrai si widget est conteneur ou l'un de ses descendants.

    Compare les chemins Tk complets : « .!ctkentry » ne contient pas « .!ctkentry5 ».
    """
    if widget is None:
        return False
    chemin, base = str(widget), str(conteneur)
    return chemin == base or chemin.startswith(base + ".")


class Carte(ctk.CTkFrame):
    """Cadre arrondi, posé sur le fond de la fenêtre."""

    def __init__(self, parent: ctk.CTkBaseClass, **options) -> None:
        """options remplace au besoin le style par défaut (ex. border_color)."""
        style = {"fg_color": CARTE, "corner_radius": 14, "border_width": 1, "border_color": BORDURE}
        super().__init__(parent, **{**style, **options})


class Tuile(Carte):
    """Indicateur clé : petit titre, grande valeur, détail."""

    def __init__(self, parent: ctk.CTkBaseClass, titre: str, valeur: str, detail: str,
                 couleur_valeur=TEXTE) -> None:
        super().__init__(parent)
        etiquette_titre(self, titre).pack(anchor="w", padx=18, pady=(16, 0))
        ctk.CTkLabel(self, text=valeur, font=police(30, True), text_color=couleur_valeur).pack(anchor="w", padx=18)
        texte_long(self, detail, 12, conteneur=self, marge=40).pack(anchor="w", fill="x", padx=18, pady=(0, 16))


def etiquette_titre(parent: ctk.CTkBaseClass, texte: str) -> ctk.CTkLabel:
    """Petit titre de section en majuscules discrètes."""
    return ctk.CTkLabel(parent, text=texte.upper(), font=police(11, True), text_color=TEXTE_DISCRET)


def texte_long(parent: ctk.CTkBaseClass, texte: str = "", taille: int = 13,
               couleur_texte=TEXTE_SECONDAIRE, conteneur: ctk.CTkBaseClass | None = None,
               marge: int = 40) -> ctk.CTkLabel:
    """Étiquette multiligne dont le retour à la ligne suit la largeur de conteneur."""
    etiquette = ctk.CTkLabel(parent, text=texte, font=police(taille), text_color=couleur_texte,
                             justify="left", anchor="w", wraplength=400)

    def ajuster(evenement) -> None:
        echelle = ctk.ScalingTracker.get_widget_scaling(etiquette)
        etiquette.configure(wraplength=max(120, evenement.width / echelle - marge))

    (conteneur or parent).bind("<Configure>", ajuster, add="+")
    return etiquette


def bouton_principal(parent: ctk.CTkBaseClass, texte: str, commande: Callable[[], None],
                     **options) -> ctk.CTkButton:
    """Bouton d'action principale (accent) ; options remplace au besoin le style par défaut."""
    style = {"fg_color": ACCENT, "hover_color": ACCENT_SURVOL, "text_color": TEXTE_SUR_ACCENT,
             "font": police(14, True), "height": 40, "corner_radius": 10}
    return ctk.CTkButton(parent, text=texte, command=commande, **{**style, **options})


def bouton_secondaire(parent: ctk.CTkBaseClass, texte: str, commande: Callable[[], None],
                      couleur_texte=TEXTE, **options) -> ctk.CTkButton:
    """Bouton discret, contour seulement ; options remplace au besoin le style par défaut."""
    style = {"fg_color": "transparent", "hover_color": SURVOL, "border_width": 1, "border_color": BORDURE,
             "text_color": couleur_texte, "font": police(13), "height": 36, "corner_radius": 10}
    return ctk.CTkButton(parent, text=texte, command=commande, **{**style, **options})


def pastille(parent: ctk.CTkBaseClass, texte: str, commande: Callable[[], None]) -> ctk.CTkButton:
    """Petit bouton arrondi teinté de l'accent (ex. un champ conseillé à remplir)."""
    return ctk.CTkButton(parent, text=texte, command=commande, fg_color=ACCENT_DOUX, hover_color=SURVOL,
                         text_color=ACCENT, font=police(12, True), height=28, corner_radius=14, width=0)


def selecteur(parent: ctk.CTkBaseClass, choix: list[str], commande: Callable[[str], None]) -> ctk.CTkSegmentedButton:
    """Boutons segmentés (un seul choix actif), utilisés pour choisir un graphique."""
    bouton = ctk.CTkSegmentedButton(parent, values=choix, command=commande, font=police(12), height=32,
                                    corner_radius=8, fg_color=SAISIE, selected_color=ACCENT,
                                    selected_hover_color=ACCENT_SURVOL, unselected_color=SAISIE,
                                    unselected_hover_color=SURVOL, text_color=TEXTE)
    bouton.set(choix[0])
    return bouton


class InfoBulle:
    """Petite fenêtre d'explication qui apparaît quand la souris reste sur un widget."""

    DELAI_MS = 350

    def __init__(self, widget: tk.Misc, texte: str) -> None:
        """Attache la bulle à widget ; texte est l'explication affichée (modifiable ensuite)."""
        self._widget = widget
        self.texte = texte
        self._fenetre: tk.Toplevel | None = None
        self._minuterie: str | None = None
        widget.bind("<Enter>", self._planifier, add="+")
        widget.bind("<Leave>", self._cacher, add="+")
        widget.bind("<ButtonPress>", self._cacher, add="+")

    def _planifier(self, _evenement=None) -> None:
        self._annuler()
        self._minuterie = self._widget.after(self.DELAI_MS, self._montrer)

    def _annuler(self) -> None:
        if self._minuterie is not None:
            self._widget.after_cancel(self._minuterie)
            self._minuterie = None

    def _montrer(self) -> None:
        """Affiche la bulle juste sous le widget, aux couleurs du thème actif."""
        self._minuterie = None
        if self._fenetre is not None:
            return
        x = self._widget.winfo_rootx()
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
        self._fenetre = tk.Toplevel(self._widget)
        self._fenetre.wm_overrideredirect(True)
        self._fenetre.wm_geometry(f"+{x}+{y}")
        cadre = tk.Frame(self._fenetre, background=couleur(BORDURE), padx=1, pady=1)
        cadre.pack()
        tk.Label(cadre, text=self.texte, justify="left", wraplength=320, padx=10, pady=8,
                 background=couleur(CARTE), foreground=couleur(TEXTE), font=(POLICE, 10)).pack()

    def _cacher(self, _evenement=None) -> None:
        self._annuler()
        if self._fenetre is not None:
            self._fenetre.destroy()
            self._fenetre = None


class Champ:
    """Ligne du formulaire : libellé, aide et bulle à gauche ; saisie à droite ; erreur dessous.

    La saisie dépend du type : rangée de boutons pour une courte liste de choix, liste
    déroulante pour une longue, zone de texte pour un nombre (on peut donc y taper une valeur
    invalide, qui est refusée avec un message). Occupe trois lignes de la grille du parent :
    libellé et saisie côte à côte (ou l'une sous l'autre en mode compact), puis l'erreur.
    """

    LIGNES = 3

    def __init__(self, parent: ctk.CTkBaseClass, variable: Variable, ligne: int,
                 au_changement: Callable[[], None], explication: str = "") -> None:
        """Crée les widgets à partir de la ligne ligne ; au_changement est appelé à chaque modification."""
        self._variable = variable
        self._au_changement = au_changement
        self._ligne = ligne
        self._textes = textes = ctk.CTkFrame(parent, fg_color="transparent")
        titre = ctk.CTkFrame(textes, fg_color="transparent")
        titre.pack(anchor="w")
        self._libelle = ctk.CTkLabel(titre, text=variable.libelle, font=police(13), text_color=TEXTE_SECONDAIRE,
                                     height=20, anchor="w")
        self._libelle.pack(side="left")
        if explication:
            info = ctk.CTkLabel(titre, text=" ⓘ", font=police(13), text_color=ACCENT, height=20, cursor="hand2")
            info.pack(side="left")
            InfoBulle(info, explication)
        self._coche = ctk.CTkLabel(titre, text=" ✓", font=police(13, True), text_color=SUCCES, height=20)
        ctk.CTkLabel(textes, text=self._aide(), font=police(11), text_color=TEXTE_DISCRET, height=16,
                     anchor="w").pack(anchor="w")

        self._boutons = choix_en_boutons(variable)
        self._liste = self._boutons is None and isinstance(variable, VariableCategorielle)
        if self._boutons is not None:
            self._widget = ctk.CTkFrame(parent, fg_color="transparent")
            self._segments = ctk.CTkSegmentedButton(
                self._widget, values=list(self._boutons), command=lambda _: self._modifie(), height=32,
                corner_radius=8, font=police(12), fg_color=SAISIE, selected_color=ACCENT,
                selected_hover_color=ACCENT_SURVOL, unselected_color=SAISIE, unselected_hover_color=SURVOL,
                text_color=TEXTE)
            self._segments.set("")
            self._segments.pack(side="left")
            self._vider = ctk.CTkButton(self._widget, text="✕", width=26, height=26, corner_radius=13,
                                        fg_color="transparent", hover_color=SURVOL, text_color=TEXTE_DISCRET,
                                        font=police(11), command=self.effacer)
            InfoBulle(self._vider, "Laisser ce champ vide")
        elif self._liste:
            self._widget = ctk.CTkOptionMenu(
                parent, values=[NON_RENSEIGNE, *variable.choix()], command=lambda _: self._modifie(),
                width=LARGEUR_SAISIE, height=34, corner_radius=8, fg_color=SAISIE, button_color=SAISIE,
                button_hover_color=SURVOL, text_color=TEXTE_DISCRET, dropdown_fg_color=CARTE,
                dropdown_hover_color=SURVOL, dropdown_text_color=TEXTE, font=police(13),
                dropdown_font=police(13), anchor="w", dynamic_resizing=False)
            self._widget.set(NON_RENSEIGNE)
        else:
            self._widget = ctk.CTkEntry(parent, width=LARGEUR_SAISIE, height=34, corner_radius=8, border_width=1,
                                        fg_color=SAISIE, border_color=BORDURE, text_color=TEXTE,
                                        placeholder_text=f"ex. {variable.formater(variable.valeur_typique)}",
                                        placeholder_text_color=TEXTE_DISCRET, font=police(13))
            self._widget.bind("<KeyRelease>", lambda _: self._modifie())
            # Vérifié seulement quand l'utilisateur quitte vraiment le champ (voir _quitte).
            self._widget.bind("<FocusOut>", lambda _: self._widget.after(120, self._quitte))
        self._message = ctk.CTkLabel(parent, text="", font=police(11), text_color=ERREUR, height=16)
        self.adapter(compact=False)
        self._message.grid_remove()

    def adapter(self, compact: bool) -> None:
        """Côte à côte (fenêtre large) ou saisie sous le libellé (fenêtre étroite)."""
        ligne = self._ligne
        if compact:
            self._textes.grid(row=ligne, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 0))
            self._widget.grid(row=ligne + 1, column=0, columnspan=2, sticky="w", padx=18, pady=(4, 0))
        else:
            self._textes.grid(row=ligne, column=0, columnspan=1, sticky="w", padx=(18, 12), pady=(8, 0))
            self._widget.grid(row=ligne, column=1, columnspan=1, sticky="e", padx=(0, 18), pady=(8, 0))
        affiche = bool(self._message.winfo_manager())  # une erreur est-elle affichée en ce moment ?
        self._message.grid(row=ligne + 2, column=0, columnspan=2, sticky="w" if compact else "e", padx=18)
        if not affiche:
            self._message.grid_remove()

    @property
    def variable(self) -> Variable:
        """Variable saisie dans ce champ."""
        return self._variable

    @property
    def widget(self) -> ctk.CTkBaseClass:
        """Widget de saisie (pour placer le curseur ou faire défiler jusqu'à lui)."""
        return self._widget

    def _aide(self) -> str:
        """Intervalle permis (nombres) et valeur typique."""
        variable = self._variable
        typique = variable.formater(variable.valeur_typique)
        if isinstance(variable, VariableNumerique):
            return (f"Entre {variable.formater(variable.minimum)} et {variable.formater(variable.maximum)}"
                    f" · typique {typique}")
        return f"Typique : {typique.split(' — ', 1)[-1]}"

    def _modifie(self) -> None:
        """Efface l'erreur affichée, met à jour l'apparence « rempli / vide », prévient la page."""
        self.marquer_erreur(None)
        rempli = self.texte() not in ("", NON_RENSEIGNE)
        if self._liste:
            self._widget.configure(text_color=TEXTE if rempli else TEXTE_DISCRET)
        if self._boutons is not None:
            if rempli:
                self._vider.pack(side="left", padx=(4, 0))
            else:
                self._vider.pack_forget()
        self._libelle.configure(text_color=TEXTE if rempli else TEXTE_SECONDAIRE)
        if rempli:
            self._coche.pack(side="left")
        else:
            self._coche.pack_forget()
        self._au_changement()

    def _quitte(self) -> None:
        """Vérifie la saisie si le curseur n'est plus dans ce champ.

        Un graphique redessiné peut voler le focus un instant puis le rendre : dans ce cas,
        l'utilisateur est toujours en train de taper et on ne l'interrompt pas.
        """
        try:
            focus = self._widget.focus_lastfor()  # dernier widget à avoir le focus dans cette fenêtre
        except (KeyError, tk.TclError):  # widget détruit entre-temps
            focus = None
        if not est_dans(focus, self._widget):
            self.verifier()

    def texte(self) -> str:
        """Texte actuellement saisi ou choisi (vide si rien n'est saisi)."""
        if self._boutons is not None:
            return self._boutons.get(self._segments.get(), "")
        return self._widget.get()

    def definir(self, texte: str) -> None:
        """Remplace le contenu du champ (texte vide ou « non renseigné » : champ vide)."""
        if self._boutons is not None:
            court = next((court for court, complet in self._boutons.items() if texte in (court, complet)), "")
            self._segments.set(court)
        elif self._liste:
            self._widget.set(texte or NON_RENSEIGNE)
        else:
            self._widget.delete(0, "end")  # réaffiche l'exemple grisé si le champ reste vide
            if texte:
                self._widget.insert(0, texte)
        self._modifie()

    def effacer(self) -> None:
        """Remet le champ à vide."""
        self.definir("")

    def verifier(self) -> bool:
        """Valide la saisie avec la variable ; affiche l'erreur sous le champ. Renvoie True si valide."""
        try:
            self._variable.lire(self.texte())
        except DonneeInvalideError as erreur:
            self.marquer_erreur(str(erreur))
            return False
        self.marquer_erreur(None)
        return True

    def marquer_erreur(self, message: str | None) -> None:
        """Affiche message en rouge sous le champ, ou retire l'erreur si message est None."""
        if message is None:
            self._message.grid_remove()
            if self._liste:
                self._widget.configure(fg_color=SAISIE, button_color=SAISIE)
            elif self._boutons is None:
                self._widget.configure(border_color=BORDURE)
            return
        # « Âge (ans) : la valeur doit... » -> « La valeur doit... » (le libellé est déjà à gauche).
        detail = message.split(" : ", 1)[-1] if message.startswith(self._variable.libelle) else message
        self._message.configure(text=detail[:1].upper() + detail[1:])
        self._message.grid()  # reprend la position mémorisée par adapter
        if self._liste:
            self._widget.configure(fg_color=ERREUR_FOND, button_color=ERREUR_FOND)
        elif self._boutons is None:
            self._widget.configure(border_color=ERREUR)

    def donner_focus(self) -> None:
        """Place le curseur dans le champ."""
        (self._segments if self._boutons is not None else self._widget).focus_set()


class ZoneGraphique(ctk.CTkFrame):
    """Cadre qui affiche une figure Matplotlib et peut la remplacer par une autre."""

    def __init__(self, parent: ctk.CTkBaseClass) -> None:
        super().__init__(parent, fg_color=CARTE, corner_radius=0)
        self._canevas: FigureCanvasTkAgg | None = None

    def afficher(self, figure: Figure) -> None:
        """Remplace le graphique affiché par figure, sans voler le curseur de l'utilisateur.

        FigureCanvasTkAgg demande le focus pour son canevas à sa création ; Tk le lui donne
        seulement quand le canevas apparaît à l'écran, donc après coup. Quand le canevas reçoit
        ce focus, on le rend au widget qui l'avait (ex. le champ en cours de saisie).
        """
        try:
            focus = self.focus_lastfor()  # fonctionne même si la fenêtre n'est pas au premier plan
        except (KeyError, tk.TclError):
            focus = None
        if self._canevas is not None:
            self._canevas.get_tk_widget().destroy()
        self._canevas = FigureCanvasTkAgg(figure, master=self)
        widget = self._canevas.get_tk_widget()
        widget.configure(background=couleur(CARTE), highlightthickness=0, takefocus=0)
        self._canevas.draw()
        widget.pack(fill="both", expand=True)
        if focus is not None and not est_dans(focus, self):
            widget.bind("<FocusIn>", lambda _: self._rendre_focus(widget, focus))

    @staticmethod
    def _rendre_focus(canevas: tk.Misc, focus: tk.Misc) -> None:
        """Rend le focus au widget qui l'avait avant le canevas (une seule fois)."""
        canevas.unbind("<FocusIn>")
        try:
            if focus.winfo_exists():
                focus.focus_set()
        except tk.TclError:
            pass


# Une boîte du schéma : (titre écrit dans la boîte, phrase écrite dessous).
Boite = tuple[str, str]


class Schema(tk.Canvas):
    """Schéma en boîtes reliées par des flèches, aux couleurs du thème actif.

    etapes se lit de gauche à droite ; chaque étape contient une ou deux boîtes, empilées.
    Chaque boîte d'une étape est reliée à chaque boîte de l'étape suivante, et la dernière
    étape (le résultat) est mise en évidence. Si les boîtes deviennent trop étroites (fenêtre
    étroite), les étapes passent l'une sous l'autre. Le schéma se redessine quand sa largeur
    change ; dessiner() le redessine aussi après un changement de thème.
    """

    LARGEUR_MIN = 130  # largeur minimale d'une boîte côte à côte (pixels avant mise à l'échelle)
    ECART = 40         # espace des flèches entre deux étapes
    MARGE = 10         # marge intérieure des boîtes

    def __init__(self, parent: tk.Misc, etapes: list[list[Boite]]) -> None:
        super().__init__(parent, width=200, height=60, highlightthickness=0, borderwidth=0,
                         background=couleur(CARTE))
        self._etapes = etapes
        self._largeur = 0
        self._echelle = 1.0
        self._police_titre: tuple = (POLICE, -13, "bold")
        self._police_phrase: tuple = (POLICE, -12)
        self.bind("<Configure>", self._redimensionne)

    def _redimensionne(self, evenement: tk.Event) -> None:
        """Redessine seulement si la largeur change (changer la hauteur relance <Configure>)."""
        if evenement.width != self._largeur:
            self._largeur = evenement.width
            self.dessiner()

    def dessiner(self) -> None:
        """Efface et redessine tout le schéma à la largeur actuelle, puis ajuste sa hauteur."""
        self.delete("all")
        self.configure(background=couleur(CARTE))
        largeur = self.winfo_width()
        if largeur <= 1:  # pas encore affiché : <Configure> rappellera dessiner
            return
        self._echelle = ctk.ScalingTracker.get_widget_scaling(self)
        self._police_titre = (POLICE, -round(13 * self._echelle), "bold")
        self._police_phrase = (POLICE, -round(12 * self._echelle))
        nb = len(self._etapes)
        largeur_boite = (largeur - 4 - (nb - 1) * self._px(self.ECART)) / nb
        if largeur_boite >= self._px(self.LARGEUR_MIN):
            hauteur = self._dessiner_en_ligne(largeur_boite)
        else:
            hauteur = self._dessiner_en_colonne(largeur)
        if int(self.cget("height")) != hauteur:
            self.configure(height=hauteur)

    # ----- Mesures et formes ------------------------------------------------------------

    def _px(self, valeur: float) -> float:
        """Taille en pixels réels (CustomTkinter ne met pas à l'échelle un tk.Canvas)."""
        return valeur * self._echelle

    def _hauteur_texte(self, texte: str, largeur: float, police_texte: tuple) -> float:
        """Hauteur qu'occupe texte, renvoyé à la ligne dans largeur."""
        element = self.create_text(0, 0, text=texte, width=largeur, font=police_texte, anchor="nw")
        _, haut, _, bas = self.bbox(element)
        self.delete(element)
        return bas - haut

    def _hauteur_boites(self, boites: list[Boite], largeur: float) -> float:
        """Hauteur commune de ces boîtes : celle du plus long titre, plus les marges."""
        return max(self._hauteur_texte(titre, largeur - 2 * self._px(self.MARGE), self._police_titre)
                   for titre, _ in boites) + 2 * self._px(self.MARGE)

    def _boite(self, x: float, y: float, largeur: float, hauteur: float, boite: Boite, resultat: bool) -> float:
        """Dessine la boîte (coin haut gauche en x, y) et sa phrase dessous ; renvoie le bas de la phrase."""
        # Espace insécable devant « % » : « 100 % » ne doit pas être coupé en fin de ligne.
        titre, phrase = (texte.replace(" %", " %") for texte in boite)
        fond, bord, encre =(ACCENT_DOUX, ACCENT, ACCENT) if resultat else (CARTE_RELIEF, BORDURE, TEXTE)
        r = self._px(10)
        x2, y2 = x + largeur, y + hauteur
        # Polygone lissé dont chaque coin est doublé : un rectangle aux coins arrondis.
        coins = [x + r, y, x2 - r, y, x2, y, x2, y + r, x2, y2 - r, x2, y2, x2 - r, y2, x + r, y2,
                 x, y2, x, y2 - r, x, y + r, x, y]
        self.create_polygon(coins, smooth=True, fill=couleur(fond), outline=couleur(bord), width=1)
        self.create_text(x + largeur / 2, y + hauteur / 2, text=titre, width=largeur - 2 * self._px(self.MARGE),
                         font=self._police_titre, fill=couleur(encre), justify="center")
        element = self.create_text(x + largeur / 2, y2 + self._px(6), text=phrase, width=largeur,
                                   font=self._police_phrase, fill=couleur(TEXTE_SECONDAIRE), justify="center",
                                   anchor="n")
        return self.bbox(element)[3]

    def _fleche(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Flèche discrète de (x1, y1) vers (x2, y2)."""
        self.create_line(x1, y1, x2, y2, fill=couleur(TEXTE_DISCRET), width=max(1.0, self._px(1.5)),
                         arrow=tk.LAST, arrowshape=(self._px(8), self._px(10), self._px(4)))

    # ----- Dispositions -----------------------------------------------------------------

    def _dessiner_en_ligne(self, largeur_boite: float) -> int:
        """Étapes côte à côte ; une boîte seule est centrée sur les boîtes empilées. Renvoie la hauteur."""
        derniere = len(self._etapes) - 1
        hauteur_boite = max(self._hauteur_boites(boites, largeur_boite) for boites in self._etapes)
        pas = 0.0  # distance verticale entre deux boîtes empilées : boîte, phrase, espace
        for boites in self._etapes:
            for _, phrase in boites[:-1]:
                pas = max(pas, hauteur_boite + self._px(6) + self._hauteur_texte(phrase, largeur_boite,
                                                                                 self._police_phrase)
                          + self._px(18))
        bas = 2.0
        positions: list[list[tuple[float, float, float]]] = []  # (gauche, droite, milieu vertical)
        for rang, boites in enumerate(self._etapes):
            x = 2 + rang * (largeur_boite + self._px(self.ECART))
            premier = 2 + pas * (2 - len(boites)) / 2  # une boîte seule se place à mi-hauteur
            positions.append([])
            for indice, boite in enumerate(boites):
                y = premier + indice * pas
                bas = max(bas, self._boite(x, y, largeur_boite, hauteur_boite, boite, rang == derniere))
                positions[-1].append((x, x + largeur_boite, y + hauteur_boite / 2))
        espace = self._px(4)
        for depart, arrivee in zip(positions, positions[1:]):
            for _, droite, y1 in depart:
                for gauche, _, y2 in arrivee:
                    self._fleche(droite + espace, y1, gauche - espace, y2)
        return int(bas + 4)

    def _dessiner_en_colonne(self, largeur: float) -> int:
        """Étapes l'une sous l'autre (fenêtre étroite), deux boîtes d'une étape côte à côte ; renvoie la hauteur."""
        derniere = len(self._etapes) - 1
        ecart = self._px(14)
        y, bas = 2.0, 2.0
        precedente: list[float] = []  # milieux horizontaux des boîtes de l'étape précédente
        for rang, boites in enumerate(self._etapes):
            largeur_boite = (largeur - 4 - (len(boites) - 1) * ecart) / len(boites)
            hauteur_boite = self._hauteur_boites(boites, largeur_boite)
            milieux = [2 + indice * (largeur_boite + ecart) + largeur_boite / 2 for indice in range(len(boites))]
            for x1 in precedente:
                for x2 in milieux:
                    self._fleche(x1, y - self._px(28), x2, y - self._px(4))
            for milieu, boite in zip(milieux, boites):
                bas = max(bas, self._boite(milieu - largeur_boite / 2, y, largeur_boite, hauteur_boite, boite,
                                           rang == derniere))
            precedente = milieux
            y = bas + self._px(32)
        return int(bas + 4)
