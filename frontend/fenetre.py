"""Fenêtre principale CustomTkinter : barre latérale de navigation, pages, thème clair ou sombre.

Elle ne fait aucun calcul : elle crée les pages, qui appellent la classe Application.
Sous LARGEUR_COMPACTE (écran de portable, projecteur), la barre latérale se réduit aux
icônes et l'avertissement passe dans un bandeau au-dessus de la page.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
import matplotlib

from frontend.application import Application, pourcentage
from frontend.composants import InfoBulle, etiquette_titre, texte_long
from frontend.pages import PageAPropos, PageHistorique, PageModele, PagePrediction
from frontend.theme import (ACCENT_DOUX, AVERTISSEMENT, AVERTISSEMENT_FOND, BARRE_LATERALE, BORDURE, CARTE,
                            FOND, SURVOL, TEXTE, TEXTE_DISCRET, TEXTE_SECONDAIRE, basculer_theme,
                            configurer_tableaux, mode_sombre, police)
from backend.entrainement import entrainer_et_sauvegarder
from backend.exceptions import DonneeInvalideError, ErreurProjet, FichierIntrouvableError

NAVIGATION = [("prediction", "◉", "Prédiction"), ("modele", "▦", "Le modèle"),
              ("historique", "☰", "Historique"), ("a_propos", "ⓘ", "À propos")]

# Seule mise en garde exigée par l'énoncé (section 4, domaine sensible : l'emploi).
TEXTE_AVERTISSEMENT = "Exercice pédagogique, pas une aide à la décision."

# Largeur (en pixels avant mise à l'échelle) sous laquelle la fenêtre passe en mode compact.
LARGEUR_COMPACTE = 1180


class FenetrePrincipale(ctk.CTk):
    """Fenêtre de l'application : contient l'Application et les quatre pages (composition)."""

    def __init__(self) -> None:
        """Crée la fenêtre vide, centrée ; installer() y ajoute ensuite le contenu."""
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=FOND)
        self.title("Risque de départ d'un employé — INF1007")
        # Taille de repli si la fenêtre ne peut pas être agrandie (voir maximiser).
        ecran_l, ecran_h = self.winfo_screenwidth(), self.winfo_screenheight()
        largeur, hauteur = int(min(1500, ecran_l - 40)), int(min(930, ecran_h - 90))
        self.geometry(f"{largeur}x{hauteur}+{int((ecran_l - largeur) / 2)}+{max(0, int((ecran_h - hauteur) / 2) - 20)}")
        self.minsize(940, 620)
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        self._pages: dict[str, ctk.CTkBaseClass] = {}
        self._boutons: dict[str, list[ctk.CTkButton]] = {cle: [] for cle, _, _ in NAVIGATION}
        self._boutons_theme: list[ctk.CTkButton] = []
        self._page_active = ""
        self._compact: bool | None = None

    def installer(self, application: Application) -> None:
        """Construit les deux barres latérales, le bandeau d'avertissement, les pages et les raccourcis."""
        configurer_tableaux(self, ctk.ScalingTracker.get_window_scaling(self))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._barre_large = self._construire_barre_large(application)
        self._barre_compacte = self._construire_barre_compacte()

        droite = ctk.CTkFrame(self, fg_color="transparent")
        droite.grid(row=0, column=1, sticky="nsew", padx=22, pady=18)
        droite.columnconfigure(0, weight=1)
        droite.rowconfigure(1, weight=1)
        self._bandeau = ctk.CTkFrame(droite, fg_color=AVERTISSEMENT_FOND, corner_radius=10, border_width=1,
                                     border_color=AVERTISSEMENT)
        ctk.CTkLabel(self._bandeau, text=f"⚠  {TEXTE_AVERTISSEMENT}", font=police(12),
                     text_color=AVERTISSEMENT).pack(anchor="w", padx=12, pady=4)

        conteneur = ctk.CTkFrame(droite, fg_color="transparent")
        conteneur.grid(row=1, column=0, sticky="nsew")
        conteneur.columnconfigure(0, weight=1)
        conteneur.rowconfigure(0, weight=1)
        prediction = PagePrediction(conteneur, application, lambda: self._pages["historique"].rafraichir())
        self._pages = {"prediction": prediction,
                       "modele": PageModele(conteneur, application),
                       "historique": PageHistorique(conteneur, application, self._recharger),
                       "a_propos": PageAPropos(conteneur)}
        self.afficher_page("prediction")
        self._adapter_largeur()

        self.bind("<Return>", self._touche_entree)
        self.bind("<Control-Delete>", lambda _: self._pages["prediction"].effacer())
        self.bind("<Control-t>", lambda _: self.changer_theme())
        self.bind("<Control-T>", lambda _: self.changer_theme())
        for rang, (cle, _, _) in enumerate(NAVIGATION, start=1):
            self.bind(f"<Control-Key-{rang}>", lambda _, c=cle: self.afficher_page(c))
        self.bind("<Configure>", self._redimensionnee, add="+")

    # ----- Barres latérales -----------------------------------------------------------

    def _bouton_navigation(self, parent: ctk.CTkFrame, cle: str, rang: int, compact: bool) -> ctk.CTkButton:
        """Bouton de la page cle (icône seule si compact) ; mémorisé pour le mettre en évidence."""
        _, icone, nom = NAVIGATION[rang - 1]
        bouton = ctk.CTkButton(parent, text=icone if compact else f"{icone}    {nom}",
                               anchor="center" if compact else "w", height=42, width=46 if compact else 140,
                               corner_radius=10, fg_color="transparent", hover_color=SURVOL,
                               text_color=TEXTE_SECONDAIRE, font=police(14), command=lambda: self.afficher_page(cle))
        self._boutons[cle].append(bouton)
        InfoBulle(bouton, f"{nom} (Ctrl+{rang})")
        return bouton

    def _bouton_theme(self, parent: ctk.CTkFrame, compact: bool) -> ctk.CTkButton:
        """Bouton qui bascule entre le thème clair et le thème sombre."""
        bouton = ctk.CTkButton(parent, text="", height=36, corner_radius=10, fg_color="transparent",
                               hover_color=SURVOL, border_width=1, border_color=BORDURE, text_color=TEXTE_SECONDAIRE,
                               font=police(13), command=self.changer_theme, width=44 if compact else 140)
        bouton.compact = compact
        self._boutons_theme.append(bouton)
        InfoBulle(bouton, "Changer de thème (Ctrl+T). Le thème clair est plus lisible au projecteur.")
        return bouton

    def _construire_barre_large(self, application: Application) -> ctk.CTkFrame:
        """Nom de l'application, navigation, thème, avertissement et résumé du modèle actif."""
        barre = ctk.CTkFrame(self, fg_color=BARRE_LATERALE, corner_radius=0, width=250)
        barre.pack_propagate(False)
        ctk.CTkFrame(barre, width=1, fg_color=BORDURE, corner_radius=0).pack(side="right", fill="y")

        ctk.CTkLabel(barre, text="Risque de départ", font=police(20, True), text_color=TEXTE).pack(
            anchor="w", padx=24, pady=(28, 0))
        ctk.CTkLabel(barre, text="IBM HR Analytics · INF1007", font=police(12), text_color=TEXTE_DISCRET).pack(
            anchor="w", padx=24, pady=(0, 28))
        etiquette_titre(barre, "Navigation").pack(anchor="w", padx=24, pady=(0, 6))
        for rang, (cle, _, _) in enumerate(NAVIGATION, start=1):
            self._bouton_navigation(barre, cle, rang, compact=False).pack(fill="x", padx=14, pady=2)
        self._bouton_theme(barre, compact=False).pack(anchor="w", padx=14, pady=(18, 0))

        meta = application.metadonnees
        retenu = meta["metriques_test"][meta["modele"]]
        resume = ctk.CTkFrame(barre, fg_color=CARTE, corner_radius=12, border_width=1, border_color=BORDURE)
        resume.pack(side="bottom", fill="x", padx=14, pady=18)
        etiquette_titre(resume, "Modèle actif").pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(resume, text=meta["modele"], font=police(14, True), text_color=TEXTE).pack(anchor="w", padx=14)
        ctk.CTkLabel(resume, text=f"Précision {pourcentage(retenu['exactitude_equilibree'])} · "
                                  f"AUC {retenu.get('auc', 0.5):.2f}".replace(".", ","),
                     font=police(12), text_color=TEXTE_SECONDAIRE).pack(anchor="w", padx=14, pady=(0, 12))

        # Avertissement exigé par l'énoncé (domaine de l'emploi) : visible sur toutes les pages.
        avertissement = ctk.CTkFrame(barre, fg_color=AVERTISSEMENT_FOND, corner_radius=12, border_width=1,
                                     border_color=AVERTISSEMENT)
        avertissement.pack(side="bottom", fill="x", padx=14)
        texte_long(avertissement, f"⚠  {TEXTE_AVERTISSEMENT}", 12, AVERTISSEMENT, conteneur=avertissement,
                   marge=30).pack(anchor="w", fill="x", padx=14, pady=10)
        return barre

    def _construire_barre_compacte(self) -> ctk.CTkFrame:
        """Barre étroite : seulement les icônes des pages et le bouton de thème."""
        barre = ctk.CTkFrame(self, fg_color=BARRE_LATERALE, corner_radius=0, width=72)
        barre.pack_propagate(False)
        ctk.CTkFrame(barre, width=1, fg_color=BORDURE, corner_radius=0).pack(side="right", fill="y")
        ctk.CTkLabel(barre, text="RD", font=police(16, True), text_color=TEXTE).pack(pady=(24, 22))
        for rang, (cle, _, _) in enumerate(NAVIGATION, start=1):
            self._bouton_navigation(barre, cle, rang, compact=True).pack(padx=12, pady=2)
        self._bouton_theme(barre, compact=True).pack(side="bottom", pady=18)
        return barre

    # ----- Thème et taille ------------------------------------------------------------

    def changer_theme(self) -> None:
        """Bascule clair / sombre ; les tableaux et les graphiques sont redessinés."""
        # Sous Windows, CustomTkinter cache et réaffiche la fenêtre pour recolorer sa barre de titre,
        # puis rend le focus au widget qui l'avait : ce ne doit pas être un graphique qui va être recréé.
        self.focus_set()
        basculer_theme()
        configurer_tableaux(self, ctk.ScalingTracker.get_window_scaling(self))
        for page in self._pages.values():
            page.changer_theme()
        self._maj_boutons_theme()

    def _maj_boutons_theme(self) -> None:
        """Le bouton annonce le thème vers lequel il bascule."""
        icone, texte = ("☀", "Thème clair") if mode_sombre() else ("☾", "Thème sombre")
        for bouton in self._boutons_theme:
            bouton.configure(text=icone if bouton.compact else f"{icone}   {texte}")

    def _redimensionnee(self, evenement: tk.Event) -> None:
        """Appelé quand un widget change de taille ; seule la fenêtre elle-même nous intéresse."""
        if evenement.widget is self:
            self._adapter_largeur()

    def _adapter_largeur(self) -> None:
        """Passe en mode compact (ou en sort) selon la largeur de la fenêtre."""
        largeur = self.winfo_width() / ctk.ScalingTracker.get_window_scaling(self)
        compact = 1 < largeur < LARGEUR_COMPACTE
        if compact == self._compact:
            return
        self._compact = compact
        (self._barre_large if compact else self._barre_compacte).grid_forget()
        (self._barre_compacte if compact else self._barre_large).grid(row=0, column=0, sticky="ns")
        if compact:
            self._bandeau.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        else:
            self._bandeau.grid_remove()
        self._pages["prediction"].adapter(compact)
        self._maj_boutons_theme()

    # ----- Navigation -----------------------------------------------------------------

    def maximiser(self) -> None:
        """Agrandit la fenêtre à tout l'écran (Windows : « zoomed », Linux : -zoomed)."""
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass  # la taille de repli choisie dans __init__ reste en place

    def afficher_page(self, cle: str) -> None:
        """Affiche la page demandée et met en évidence son bouton dans les deux barres."""
        for nom, page in self._pages.items():
            if nom != cle:
                page.grid_remove()
        self._pages[cle].grid(row=0, column=0, sticky="nsew")
        for nom, boutons in self._boutons.items():
            for bouton in boutons:
                actif = nom == cle
                bouton.configure(fg_color=ACCENT_DOUX if actif else "transparent",
                                 text_color=TEXTE if actif else TEXTE_SECONDAIRE)
        self._page_active = cle
        if cle == "historique":
            self._pages[cle].rafraichir()

    def _recharger(self, saisies: dict[str, str]) -> None:
        """Remet une prédiction de l'historique dans le formulaire et affiche la page Prédiction."""
        self._pages["prediction"].remplir(saisies, "Saisies rechargées depuis l'historique. Modifiez-les au "
                                                   "besoin, puis cliquez sur « Prédire ».")
        self.afficher_page("prediction")

    def _touche_entree(self, _evenement=None) -> None:
        """Entrée lance la prédiction quand la page Prédiction est affichée."""
        if self._page_active == "prediction":
            self._pages["prediction"].predire()

    def _fermer(self) -> None:
        """Ferme proprement la fenêtre (et arrête la boucle Tkinter)."""
        self.quit()
        self.destroy()


def _charger_application(fenetre: FenetrePrincipale, message: ctk.CTkLabel) -> Application | None:
    """Charge le modèle sauvegardé ; propose de l'entraîner s'il manque ou s'il est illisible.

    Renvoie None si l'utilisateur refuse ou si l'entraînement échoue.
    """
    try:
        return Application.depuis_fichiers()
    except FichierIntrouvableError:
        raison = "Le modèle n'a pas encore été entraîné."
    except DonneeInvalideError as erreur:
        raison = f"Le modèle enregistré ne peut pas être utilisé :\n{erreur}"
    if not messagebox.askyesno("Modèle à entraîner", f"{raison}\n\nVoulez-vous l'entraîner maintenant ? "
                               "(environ 30 secondes)", parent=fenetre):
        return None
    message.configure(text="Entraînement du modèle en cours (environ 30 secondes)…")
    fenetre.update()
    try:
        entrainer_et_sauvegarder()
        return Application.depuis_fichiers()
    except ErreurProjet as erreur:
        messagebox.showerror("Entraînement impossible", str(erreur), parent=fenetre)
        return None


def lancer_interface() -> None:
    """Ouvre la fenêtre principale et attend que l'utilisateur la ferme."""
    matplotlib.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
    fenetre = FenetrePrincipale()
    fenetre.maximiser()
    # La fenêtre est visible pendant le chargement : un éventuel message apparaît devant elle.
    message = ctk.CTkLabel(fenetre, text="Chargement du modèle…", font=police(16), text_color=TEXTE_SECONDAIRE)
    message.place(relx=0.5, rely=0.5, anchor="center")
    fenetre.update()
    application = _charger_application(fenetre, message)
    if application is None:
        fenetre.destroy()
        return
    message.destroy()
    fenetre.installer(application)
    fenetre.mainloop()
