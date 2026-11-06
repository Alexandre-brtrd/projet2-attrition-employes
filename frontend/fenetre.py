"""Fenêtre principale CustomTkinter (thème sombre) : barre latérale de navigation et pages.

Elle ne fait aucun calcul : elle crée les pages, qui appellent la classe Application.
"""

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
import matplotlib

from frontend.composants import etiquette_titre, texte_long
from frontend.pages import PageAPropos, PageHistorique, PageModele, PagePrediction
from frontend.theme import (ACCENT_DOUX, AVERTISSEMENT, AVERTISSEMENT_FOND, BARRE_LATERALE, BORDURE,
                                       CARTE, FOND, SURVOL, TEXTE, TEXTE_DISCRET, TEXTE_SECONDAIRE,
                                       configurer_tableaux, police)
from frontend.application import Application, pourcentage
from backend.entrainement import entrainer_et_sauvegarder
from backend.exceptions import DonneeInvalideError, ErreurProjet, FichierIntrouvableError

NAVIGATION = [("prediction", "◉", "Prédiction"), ("modele", "▦", "Le modèle"),
              ("historique", "☰", "Historique"), ("a_propos", "ⓘ", "À propos")]

TEXTE_AVERTISSEMENT = ("Données fictives ; le modèle se trompe environ une fois sur quatre. Ne jamais l'utiliser "
                       "pour une décision concernant un employé réel.")


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
        self.minsize(1100, 680)
        self.protocol("WM_DELETE_WINDOW", self._fermer)
        self._pages: dict[str, ctk.CTkBaseClass] = {}
        self._boutons: dict[str, ctk.CTkButton] = {}
        self._page_active = ""

    def installer(self, application: Application) -> None:
        """Construit la barre latérale, le bandeau d'avertissement et les pages."""
        configurer_tableaux(self, ctk.ScalingTracker.get_window_scaling(self))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._construire_barre_laterale(application)

        conteneur = ctk.CTkFrame(self, fg_color="transparent")
        conteneur.grid(row=0, column=1, sticky="nsew", padx=22, pady=18)
        conteneur.columnconfigure(0, weight=1)
        conteneur.rowconfigure(0, weight=1)
        historique = PageHistorique(conteneur, application)
        self._pages = {"prediction": PagePrediction(conteneur, application, historique.rafraichir),
                       "modele": PageModele(conteneur, application),
                       "historique": historique,
                       "a_propos": PageAPropos(conteneur)}
        self.afficher_page("prediction")
        self.bind("<Return>", self._touche_entree)

    def _construire_barre_laterale(self, application: Application) -> None:
        """Nom de l'application, navigation et résumé du modèle actif."""
        barre = ctk.CTkFrame(self, fg_color=BARRE_LATERALE, corner_radius=0, width=250)
        barre.grid(row=0, column=0, sticky="ns")
        barre.pack_propagate(False)
        ctk.CTkFrame(barre, width=1, fg_color=BORDURE, corner_radius=0).pack(side="right", fill="y")

        ctk.CTkLabel(barre, text="Risque de départ", font=police(20, True), text_color=TEXTE).pack(
            anchor="w", padx=24, pady=(28, 0))
        ctk.CTkLabel(barre, text="IBM HR Analytics · INF1007", font=police(12), text_color=TEXTE_DISCRET).pack(
            anchor="w", padx=24, pady=(0, 28))
        etiquette_titre(barre, "Navigation").pack(anchor="w", padx=24, pady=(0, 6))
        for cle, icone, texte in NAVIGATION:
            bouton = ctk.CTkButton(barre, text=f"{icone}    {texte}", anchor="w", height=42, corner_radius=10,
                                   fg_color="transparent", hover_color=SURVOL, text_color=TEXTE_SECONDAIRE,
                                   font=police(14), command=lambda c=cle: self.afficher_page(c))
            bouton.pack(fill="x", padx=14, pady=2)
            self._boutons[cle] = bouton

        meta = application.metadonnees
        retenu = meta["metriques_test"][meta["modele"]]
        resume = ctk.CTkFrame(barre, fg_color=CARTE, corner_radius=12, border_width=1, border_color=BORDURE)
        resume.pack(side="bottom", fill="x", padx=14, pady=18)
        etiquette_titre(resume, "Modèle actif").pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(resume, text=meta["modele"], font=police(14, True), text_color=TEXTE).pack(anchor="w", padx=14)
        ctk.CTkLabel(resume, text=f"Précision {pourcentage(retenu['exactitude_equilibree'])} · "
                                  f"AUC {retenu.get('auc', 0.5):.2f}".replace(".", ","),
                     font=police(12), text_color=TEXTE_SECONDAIRE).pack(anchor="w", padx=14, pady=(0, 12))

        # Avertissement obligatoire (domaine de l'emploi) : visible sur toutes les pages.
        avertissement = ctk.CTkFrame(barre, fg_color=AVERTISSEMENT_FOND, corner_radius=12, border_width=1,
                                     border_color=AVERTISSEMENT)
        avertissement.pack(side="bottom", fill="x", padx=14)
        ctk.CTkLabel(avertissement, text="⚠  Exercice pédagogique", font=police(13, True),
                     text_color=AVERTISSEMENT).pack(anchor="w", padx=14, pady=(10, 0))
        texte_long(avertissement, TEXTE_AVERTISSEMENT, 12, AVERTISSEMENT, conteneur=avertissement,
                   marge=30).pack(anchor="w", fill="x", padx=14, pady=(0, 12))

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
        """Affiche la page demandée et met en évidence son bouton de navigation."""
        for nom, page in self._pages.items():
            if nom != cle:
                page.grid_remove()
        self._pages[cle].grid(row=0, column=0, sticky="nsew")
        for nom, bouton in self._boutons.items():
            actif = nom == cle
            bouton.configure(fg_color=ACCENT_DOUX if actif else "transparent",
                             text_color=TEXTE if actif else TEXTE_SECONDAIRE)
        self._page_active = cle
        if cle == "historique":
            self._pages[cle].rafraichir()

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
