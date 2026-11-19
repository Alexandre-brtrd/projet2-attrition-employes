"""Les trois pages de la fenêtre : Prédiction, Comment ça marche, Historique.

Les pages n'effectuent aucun calcul : elles lisent les saisies, appellent l'Application
et affichent ce qu'elle renvoie. Chaque graphique est accompagné d'un court texte
« Comment lire ce graphique » écrit pour un non-informaticien.
"""

import json
from collections.abc import Callable
from tkinter import messagebox, ttk

import customtkinter as ctk

from frontend.application import (NIVEAUX_FIABILITE, SEUIL_FIABILITE_BONNE, SEUIL_FIABILITE_MOYENNE, Application,
                                  Prediction, fiabilite_depuis_texte, niveau_fiabilite, points, pourcentage)
from frontend.composants import (Boite, Carte, Champ, InfoBulle, Schema, Tuile, ZoneGraphique, bouton_principal,
                                 bouton_secondaire, etiquette_titre, pastille, selecteur, texte_long)
from frontend.graphiques import figure_effets, figure_risque_reel, figure_vide
from frontend.theme import (ACCENT, AVERTISSEMENT, BORDURE, CARTE, CARTE_RELIEF, ERREUR, FIABILITE, NIVEAUX,
                            SUCCES, SURVOL, TEXTE, TEXTE_DISCRET, TEXTE_SECONDAIRE, couleur, police, theme_graphique)
from backend.config import SEUIL_DECISION
from backend.exceptions import DonneeInvalideError, SaisieInvalideError
from backend.graphiques import figure_importances, figure_matrice_confusion
from backend.style import libelle_court

ETAPES = ("1.  Décrivez l'employé : un seul champ suffit.\n"
          "2.  Cliquez sur « Prédire » (ou appuyez sur Entrée).\n"
          "3.  Lisez le risque et ce qui pèse le plus.")


def entete(page: ctk.CTkFrame, titre: str, sous_titre: str) -> ctk.CTkFrame:
    """Titre de page et phrase d'introduction."""
    cadre = ctk.CTkFrame(page, fg_color="transparent")
    ctk.CTkLabel(cadre, text=titre, font=police(26, True), text_color=TEXTE).pack(anchor="w")
    texte_long(cadre, sous_titre, 13, conteneur=page, marge=20).pack(anchor="w", fill="x")
    return cadre


class CarteGraphique(Carte):
    """Carte qui contient un sélecteur de graphiques, le graphique choisi et son mode d'emploi.

    En mode compact, le mode d'emploi passe dans une bulle d'aide pour laisser la place au graphique.
    """

    def __init__(self, parent: ctk.CTkBaseClass, choix: list[str], commande: Callable[[str], None]) -> None:
        super().__init__(parent)
        haut = ctk.CTkFrame(self, fg_color="transparent")
        haut.pack(fill="x", padx=16, pady=(14, 4))
        self._selecteur = selecteur(haut, choix, commande)
        self._selecteur.pack(side="left")
        self._aide_compacte = ctk.CTkLabel(haut, text="ⓘ Comment lire", font=police(12), text_color=ACCENT)
        self._bulle = InfoBulle(self._aide_compacte, "")
        self.zone = ZoneGraphique(self)
        self.zone.pack(fill="both", expand=True, padx=10)
        self._cadre_lecture = ctk.CTkFrame(self, fg_color=CARTE_RELIEF, corner_radius=10)
        self._cadre_lecture.pack(fill="x", padx=12, pady=(4, 12))
        etiquette_titre(self._cadre_lecture, "Comment lire ce graphique").pack(anchor="w", padx=12, pady=(8, 0))
        self._lecture = texte_long(self._cadre_lecture, "", 12, conteneur=self._cadre_lecture, marge=30)
        self._lecture.pack(anchor="w", fill="x", padx=12, pady=(0, 10))

    def expliquer(self, texte: str) -> None:
        """Remplace le texte « Comment lire ce graphique »."""
        self._lecture.configure(text=texte)
        self._bulle.texte = texte

    def adapter(self, compact: bool) -> None:
        """Mode d'emploi sous le graphique (fenêtre large) ou dans une bulle (fenêtre étroite)."""
        if compact:
            self._cadre_lecture.pack_forget()
            self._aide_compacte.pack(side="left", padx=(12, 0))
        else:
            self._aide_compacte.pack_forget()
            self._cadre_lecture.pack(fill="x", padx=12, pady=(4, 12), after=self.zone)


class PagePrediction(ctk.CTkFrame):
    """Formulaire à gauche ; risque, fiabilité, explications et graphiques à droite."""

    GRAPHIQUES = {"Facteurs": "effets", "Que veut dire le % ?": "sens"}

    def __init__(self, parent: ctk.CTkBaseClass, application: Application,
                 apres_enregistrement: Callable[[], None]) -> None:
        """apres_enregistrement est appelé après chaque prédiction ajoutée à l'historique."""
        super().__init__(parent, fg_color="transparent")
        self._application = application
        self._apres_enregistrement = apres_enregistrement
        self._champs: dict[str, Champ] = {}
        self._progression: dict[str, ctk.CTkLabel] = {}
        self._prediction: Prediction | None = None
        self._saisies_predites: dict[str, str] = {}
        self._minuterie: str | None = None
        self._graphique = next(iter(self.GRAPHIQUES.values()))
        self._champs_conseil: list[str] = []
        self._largeur_conseils = 0
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=11, uniform="colonnes")
        self.columnconfigure(1, weight=10, uniform="colonnes")
        self._construire_formulaire()
        self._construire_resultats()
        self.maj_indicateur()
        self._afficher_graphique()

    def adapter(self, compact: bool) -> None:
        """Fenêtre étroite : chaque saisie passe sous son libellé et le mode d'emploi des
        graphiques passe dans une bulle, pour que rien ne soit coupé."""
        for champ in self._champs.values():
            champ.adapter(compact)
        self._carte_graphique.adapter(compact)
        # Message à gauche des boutons (fenêtre large) ou sous eux, sur toute la largeur.
        if compact:
            self._zone_message.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        else:
            self._zone_message.grid(row=0, column=0, columnspan=1, sticky="ew", pady=0)

    # ----- Construction ---------------------------------------------------------------

    def _construire_formulaire(self) -> None:
        """Carte de gauche : titre, exemples, champs défilants par section, boutons."""
        carte = Carte(self)
        carte.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        carte.columnconfigure(0, weight=1)
        carte.rowconfigure(3, weight=1)

        haut = ctk.CTkFrame(carte, fg_color="transparent")
        haut.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 2))
        ctk.CTkLabel(haut, text="Décrivez l'employé", font=police(22, True), text_color=TEXTE).pack(anchor="w")
        texte_long(haut, "Remplissez autant de champs que vous voulez : un champ vide est permis, "
                         "mais le résultat est moins fiable. Survolez ⓘ pour une explication.", 13,
                   conteneur=carte, marge=60).pack(anchor="w", fill="x")
        exemples = ctk.CTkFrame(carte, fg_color="transparent")
        exemples.grid(row=1, column=0, sticky="w", padx=22, pady=(10, 10))
        ctk.CTkLabel(exemples, text="Exemples réels :", font=police(12),
                     text_color=TEXTE_SECONDAIRE).pack(side="left", padx=(0, 8))
        for texte, genre, aide in (("À risque", "risque", "Un employé du test qui est réellement parti"),
                                   ("Stable", "stable", "Un employé du test qui est réellement resté"),
                                   ("Au hasard", "hasard", "N'importe quel employé du test")):
            bouton = bouton_secondaire(exemples, texte, lambda g=genre: self._charger_exemple(g), width=86,
                                       height=30, font=police(12))
            bouton.pack(side="left", padx=3)
            InfoBulle(bouton, aide)
        # Les champs vides les plus utiles, en pastilles cliquables (voir _afficher_conseils).
        self._conseils = ctk.CTkFrame(carte, fg_color="transparent")
        self._conseils.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 8))
        self._conseils.bind("<Configure>", self._conseils_redimensionnes, add="+")

        self._zone_champs = ctk.CTkScrollableFrame(carte, fg_color=CARTE, corner_radius=0,
                                                   scrollbar_button_color=BORDURE,
                                                   scrollbar_button_hover_color=SURVOL)
        self._zone_champs.grid(row=3, column=0, sticky="nsew", padx=(4, 6))
        self._zone_champs.columnconfigure(0, weight=1)
        ligne = 0
        for groupe, variables in self._application.variables_par_groupe().items():
            section = ctk.CTkFrame(self._zone_champs, fg_color="transparent")
            section.grid(row=ligne, column=0, columnspan=2, sticky="ew", padx=18, pady=(24 if ligne else 6, 2))
            ctk.CTkLabel(section, text=groupe.upper(), font=police(12, True), text_color=ACCENT).pack(side="left")
            self._progression[groupe] = ctk.CTkLabel(section, text="", font=police(12), text_color=TEXTE_DISCRET)
            self._progression[groupe].pack(side="right")
            ligne += 1
            for variable in variables:
                self._champs[variable.nom] = Champ(self._zone_champs, variable, ligne, self._planifier_maj,
                                                   self._application.explication(variable.nom))
                ligne += Champ.LIGNES

        ctk.CTkFrame(carte, height=1, fg_color=BORDURE).grid(row=4, column=0, sticky="ew", padx=1)
        pied = ctk.CTkFrame(carte, fg_color="transparent")
        pied.grid(row=5, column=0, sticky="ew", padx=22, pady=14)
        pied.columnconfigure(0, weight=1)
        self._zone_message = ctk.CTkFrame(pied, fg_color="transparent")
        self._zone_message.grid(row=0, column=0, sticky="ew")
        self._message = texte_long(self._zone_message, "", 12, conteneur=self._zone_message, marge=10)
        self._message.pack(anchor="w", fill="x")
        effacer = bouton_secondaire(pied, "Tout effacer", self.effacer, width=120)
        effacer.grid(row=0, column=1, padx=10)
        InfoBulle(effacer, "Vider le formulaire (Ctrl+Suppr)")
        predire = bouton_principal(pied, "Prédire  →", self.predire, width=150)
        predire.grid(row=0, column=2)
        InfoBulle(predire, "Calculer le risque (Entrée)")

    def _construire_resultats(self) -> None:
        """Colonne de droite : carte du résultat (risque et fiabilité), carte des graphiques."""
        colonne = ctk.CTkFrame(self, fg_color="transparent")
        colonne.grid(row=0, column=1, sticky="nsew")
        colonne.columnconfigure(0, weight=1)

        carte = Carte(colonne)
        carte.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        carte.columnconfigure((0, 1), weight=1, uniform="indicateurs")

        risque = ctk.CTkFrame(carte, fg_color="transparent")
        risque.grid(row=0, column=0, sticky="new", padx=(20, 12), pady=(14, 0))
        etiquette_titre(risque, "Risque de départ").pack(anchor="w")
        self._risque = ctk.CTkLabel(risque, text="—", font=police(38, True), text_color=TEXTE_DISCRET, height=46)
        self._risque.pack(anchor="w")
        self._badge = ctk.CTkLabel(risque, text="", font=police(12, True), corner_radius=10, height=26,
                                   fg_color="transparent")
        self._badge.pack(anchor="w", pady=(0, 6))
        self._barre_risque = ctk.CTkProgressBar(risque, height=8, corner_radius=4, fg_color=SURVOL,
                                                progress_color=TEXTE_DISCRET)
        self._barre_risque.set(0)
        self._barre_risque.pack(fill="x")

        # Jauge de fiabilité à trois niveaux, alignée sur le risque : niveau, champs remplis, jauge.
        fiabilite = ctk.CTkFrame(carte, fg_color="transparent")
        fiabilite.grid(row=0, column=1, sticky="new", padx=(12, 20), pady=(14, 0))
        titre_fiabilite = etiquette_titre(fiabilite, "Fiabilité  ⓘ")
        titre_fiabilite.pack(anchor="w")
        InfoBulle(titre_fiabilite, "Plus vous remplissez les champs importants, plus le résultat est fiable.")
        # Un peu plus petit que le risque : « Moyenne » doit tenir dans la fenêtre la plus étroite.
        self._fiabilite = ctk.CTkLabel(fiabilite, text="", font=police(32, True), height=46)
        self._fiabilite.pack(anchor="w")
        self._nb_champs = ctk.CTkLabel(fiabilite, text="", font=police(12), text_color=TEXTE_SECONDAIRE, height=26)
        self._nb_champs.pack(anchor="w", pady=(0, 6))
        jauge = ctk.CTkFrame(fiabilite, fg_color="transparent", height=8)
        jauge.pack(fill="x")
        self._jauge: list[ctk.CTkFrame] = []
        for rang in range(len(NIVEAUX_FIABILITE)):
            jauge.columnconfigure(rang, weight=1, uniform="jauge")
            segment = ctk.CTkFrame(jauge, height=8, corner_radius=4, fg_color=SURVOL)
            segment.grid(row=0, column=rang, sticky="ew", padx=(0 if rang == 0 else 4, 0))
            self._jauge.append(segment)

        textes = ctk.CTkFrame(carte, fg_color="transparent")
        textes.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(12, 14))
        self._phrase = texte_long(textes, ETAPES, 13, conteneur=carte)
        self._phrase.pack(anchor="w", fill="x")
        # Affiché seulement quand le formulaire a changé depuis la prédiction (voir maj_indicateur).
        self._perime = texte_long(textes, "Le formulaire a changé depuis cette prédiction : cliquez sur "
                                          "« Prédire » pour la mettre à jour.", 12, AVERTISSEMENT, conteneur=carte)
        self._facteurs = ctk.CTkFrame(textes, fg_color="transparent")

        self._carte_graphique = CarteGraphique(colonne, list(self.GRAPHIQUES), self._choisir_graphique)
        self._carte_graphique.grid(row=1, column=0, sticky="nsew")
        colonne.rowconfigure(1, weight=1, minsize=320)

    # ----- Réactions aux saisies ------------------------------------------------------

    def _saisies(self) -> dict[str, str]:
        """Texte de chaque champ du formulaire."""
        return {nom: champ.texte() for nom, champ in self._champs.items()}

    def _planifier_maj(self) -> None:
        """Met à jour l'indicateur 250 ms après la dernière modification (évite de recalculer à chaque touche)."""
        if self._minuterie is not None:
            self.after_cancel(self._minuterie)
        self._minuterie = self.after(250, self.maj_indicateur)

    def maj_indicateur(self) -> None:
        """Champs remplis par section, fiabilité, conseils et avertissement « formulaire modifié »."""
        self._minuterie = None
        saisies = self._saisies()
        champs = self._application.champs_renseignes(saisies)
        niveau = niveau_fiabilite(self._application.precision_attendue(champs))
        teinte = FIABILITE[niveau]
        self._fiabilite.configure(text=niveau, text_color=teinte)
        rang_niveau = NIVEAUX_FIABILITE.index(niveau)
        for rang, segment in enumerate(self._jauge):
            segment.configure(fg_color=teinte if rang <= rang_niveau else SURVOL)
        self._nb_champs.configure(text=f"{len(champs)} / {len(self._champs)} champs remplis")
        for groupe, (remplis, nombre) in self._application.progression_par_groupe(saisies).items():
            self._progression[groupe].configure(
                text=f"{remplis} / {nombre}" + ("  ✓" if remplis == nombre else ""),
                text_color=SUCCES if remplis == nombre else ACCENT if remplis else TEXTE_DISCRET)
        self._afficher_conseils(champs)
        if self._prediction is not None and saisies != self._saisies_predites:
            self._perime.pack(anchor="w", fill="x", after=self._phrase, pady=(4, 0))
        else:
            self._perime.pack_forget()

    def _conseils_redimensionnes(self, evenement) -> None:
        """Redispose les pastilles quand la largeur change (pas quand seule la hauteur change)."""
        if evenement.width != self._largeur_conseils:
            self._largeur_conseils = evenement.width
            self._afficher_conseils(self._champs_conseil)

    def _afficher_conseils(self, champs: list[str]) -> None:
        """Pastilles cliquables : les champs vides les plus utiles à remplir ensuite.

        Elles passent à la ligne suivante quand la largeur ne suffit pas (largeurs estimées
        avec la police, en pixels avant mise à l'échelle).
        """
        self._champs_conseil = list(champs)
        for enfant in self._conseils.winfo_children():
            enfant.destroy()
        conseilles = self._application.champs_conseilles(champs)
        if not conseilles:
            ctk.CTkLabel(self._conseils, text="Tous les champs sont remplis.", font=police(12),
                         text_color=SUCCES).pack(anchor="w")
            return
        reel = self._conseils.winfo_width()
        disponible = reel / ctk.ScalingTracker.get_widget_scaling(self) if reel > 1 else float("inf")
        phrase = "Pour une meilleure fiabilité, remplissez :"
        elements = [(police(12).measure(phrase) + 6,
                     lambda rangee: ctk.CTkLabel(rangee, text=phrase, font=police(12),
                                                 text_color=TEXTE_SECONDAIRE).pack(side="left", padx=(0, 6)))]
        for variable in conseilles:
            libelle = libelle_court(variable.nom)
            elements.append((police(12, True).measure(libelle) + 36, lambda rangee, nom=variable.nom, texte=libelle:
                             pastille(rangee, texte, lambda: self._defiler_vers(self._champs[nom])).pack(
                                 side="left", padx=2)))
        rangee, occupe = None, 0.0
        for largeur, creer in elements:
            if rangee is None or (occupe and occupe + largeur > disponible):
                rangee = ctk.CTkFrame(self._conseils, fg_color="transparent")
                rangee.pack(anchor="w", pady=(0 if occupe == 0 else 4, 0))
                occupe = 0.0
            creer(rangee)
            occupe += largeur

    def _choisir_graphique(self, choix: str) -> None:
        """Appelé par le sélecteur de graphique."""
        self._graphique = self.GRAPHIQUES[choix]
        self._afficher_graphique()

    def _afficher_graphique(self) -> None:
        """Dessine le graphique choisi et son mode d'emploi."""
        theme = theme_graphique()
        if self._graphique == "effets":
            if self._prediction is None:
                figure = figure_vide("Cliquez sur « Prédire » pour voir ce qui influence le résultat.", theme)
            else:
                valeurs = {nom: self._application.variable(nom).formater(valeur)
                           for nom, valeur in self._prediction.valeurs_connues.items()}
                figure = figure_effets(self._prediction.effets, valeurs, theme=theme)
            lecture = ("Rouge : l'information fait monter le risque ; vert : elle le fait baisser. "
                       "La longueur de la barre montre de combien, en points de pourcentage.")
        else:
            connus = (self._prediction.valeurs_connues if self._prediction
                      else self._application.champs_renseignes(self._saisies()))
            figure = figure_risque_reel(self._application.tranches_de_risque(connus),
                                        self._prediction.probabilite if self._prediction else None, theme=theme)
            lecture = ("Le % affiché est un score, pas une probabilité exacte. Chaque barre montre combien "
                       "d'employés du test au score semblable sont vraiment partis.")
        self._carte_graphique.zone.afficher(figure)
        self._carte_graphique.expliquer(lecture)

    def changer_theme(self) -> None:
        """Redessine le graphique aux couleurs du nouveau thème."""
        self._afficher_graphique()

    # ----- Actions --------------------------------------------------------------------

    def predire(self) -> None:
        """Valide le formulaire, affiche la prédiction et l'ajoute à l'historique."""
        for champ in self._champs.values():
            champ.marquer_erreur(None)
        saisies = self._saisies()
        try:
            prediction = self._application.predire(saisies, enregistrer=False)
        except SaisieInvalideError as erreur:
            fautifs = [nom for nom in self._champs if nom in erreur.erreurs]
            for nom in fautifs:
                self._champs[nom].marquer_erreur(erreur.erreurs[nom])
            if fautifs:
                self._defiler_vers(self._champs[fautifs[0]])
            self._afficher_message(f"{len(erreur.erreurs)} saisie(s) à corriger : voir les champs en rouge.",
                                   ERREUR)
            return
        except DonneeInvalideError as erreur:
            self._afficher_message(str(erreur), ERREUR)
            return
        self._prediction, self._saisies_predites = prediction, saisies
        self._afficher_prediction(prediction)
        try:
            self._application.enregistrer(prediction)
        except OSError as erreur:
            self._afficher_message(f"Prédiction affichée, mais l'historique n'a pas pu être enregistré "
                                   f"(fichier ouvert ailleurs ?) : {erreur}", ERREUR)
        else:
            self._afficher_message(f"Prédiction enregistrée dans l'historique à {prediction.date:%H:%M:%S}.",
                                   SUCCES)
            self._apres_enregistrement()

    def _afficher_prediction(self, prediction: Prediction) -> None:
        """Risque, badge coloré, phrase en langage courant et facteurs principaux."""
        couleur_niveau, fond = NIVEAUX[prediction.niveau]
        self._risque.configure(text=pourcentage(prediction.probabilite), text_color=couleur_niveau)
        self._badge.configure(text=f"   Risque {prediction.niveau}   ",
                              fg_color=fond, text_color=couleur_niveau)
        self._barre_risque.configure(progress_color=couleur_niveau)
        self._barre_risque.set(prediction.probabilite)
        self._phrase.configure(text=self._application.phrase_resultat(prediction))
        self._afficher_facteurs(prediction)
        self.maj_indicateur()
        self._afficher_graphique()

    def _afficher_facteurs(self, prediction: Prediction) -> None:
        """Les trois informations qui pèsent le plus, avec leur effet en points."""
        for enfant in self._facteurs.winfo_children():
            enfant.destroy()
        facteurs = self._application.facteurs_principaux(prediction)
        if not facteurs:
            self._facteurs.pack_forget()
            return
        self._facteurs.pack(anchor="w", fill="x", pady=(10, 0))
        self._facteurs.columnconfigure(1, weight=1)
        etiquette_titre(self._facteurs, "Ce qui pèse le plus").grid(row=0, column=0, columnspan=3, sticky="w")
        for rang, (libelle, valeur, effet) in enumerate(facteurs, start=1):
            teinte = NIVEAUX["très élevé"][0] if effet > 0 else NIVEAUX["faible"][0]
            ctk.CTkLabel(self._facteurs, text="▲" if effet > 0 else "▼", font=police(12), text_color=teinte,
                         height=22).grid(row=rang, column=0, sticky="w", padx=(0, 8))
            ctk.CTkLabel(self._facteurs, text=f"{libelle} = {valeur}", font=police(13), text_color=TEXTE,
                         height=22, anchor="w").grid(row=rang, column=1, sticky="w")
            ctk.CTkLabel(self._facteurs, text=points(effet), font=police(13, True), text_color=teinte,
                         height=22).grid(row=rang, column=2, sticky="e")

    def _afficher_message(self, texte: str, couleur_texte=TEXTE_SECONDAIRE) -> None:
        """Message à gauche des boutons (erreur, confirmation...)."""
        self._message.configure(text=texte, text_color=couleur_texte)

    def effacer(self) -> None:
        """Vide le formulaire et le résultat."""
        for champ in self._champs.values():
            champ.effacer()
        self._prediction, self._saisies_predites = None, {}
        self._risque.configure(text="—", text_color=TEXTE_DISCRET)
        self._badge.configure(text="", fg_color="transparent")
        self._barre_risque.configure(progress_color=TEXTE_DISCRET)
        self._barre_risque.set(0)
        self._phrase.configure(text=ETAPES)
        self._facteurs.pack_forget()
        self._afficher_message("")
        self.maj_indicateur()
        self._afficher_graphique()

    def remplir(self, saisies: dict[str, str], message: str) -> None:
        """Remplace tout le formulaire par saisies (ex. un exemple ou une ligne de l'historique)."""
        for nom, champ in self._champs.items():
            champ.definir(saisies.get(nom, ""))
        self._afficher_message(message)

    def _charger_exemple(self, genre: str) -> None:
        """Remplit le formulaire avec un vrai employé du jeu de test."""
        saisies, parti = self._application.exemple(genre)
        realite = "a réellement quitté l'entreprise" if parti else "est réellement resté"
        self.remplir(saisies, f"Exemple chargé : un véritable employé du jeu de test, qui {realite}. "
                              "Cliquez sur « Prédire » pour comparer.")

    def _defiler_vers(self, champ: Champ) -> None:
        """Fait défiler le formulaire jusqu'au champ et y place le curseur."""
        self.update_idletasks()
        interieur = champ.widget.master  # cadre intérieur du formulaire défilant
        hauteur = interieur.winfo_height()
        if hauteur > 0:
            position = max(0.0, (champ.widget.winfo_y() - 80) / hauteur)
            self._zone_champs._parent_canvas.yview_moveto(position)  # canevas interne du cadre défilant
        champ.donner_focus()


class PageFonctionnement(ctk.CTkScrollableFrame):
    """« Comment ça marche », à lire de haut en bas : fonctionnement et entraînement en schémas,
    résultats et limites, détails techniques (repliés), raccourcis clavier et sources."""

    GRAPHIQUES = {"Bonnes et mauvaises réponses": "matrice", "Variables utiles": "importances"}

    def __init__(self, parent: ctk.CTkBaseClass, application: Application) -> None:
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=BORDURE,
                         scrollbar_button_hover_color=SURVOL)
        self._meta = meta = application.metadonnees
        lignes = meta["lignes"]
        precision = meta["metriques_test"][meta["modele"]]["exactitude_equilibree"]
        hasard = pourcentage(meta["metriques_test"]["Référence (classe majoritaire)"]["exactitude_equilibree"])
        entete(self, "Comment ça marche",
               f"L'application estime le risque qu'un employé quitte son entreprise à partir de son profil "
               f"(jusqu'à {len(application.variables)} informations), avec un modèle qui a appris sur "
               f"{lignes['total']} employés fictifs.").pack(anchor="w", fill="x", padx=4, pady=(0, 14))

        self._schemas = [
            self._carte_schema("Comment le modèle décide", [
                [("Profil de l'employé", "Les champs que vous remplissez ; un champ vide est permis.")],
                [(f"Modèle ({meta['modele'].lower()})", "Il pèse chaque information selon ce qu'il a appris.")],
                [("Score de risque", "Un pourcentage entre 0 et 100 %.")],
                [("Départ probable / Reste", f"Départ probable si le score atteint {pourcentage(SEUIL_DECISION)} ; "
                                             "sinon, l'employé reste.")],
            ]),
            self._carte_schema("Comment il a appris, puis a été vérifié", [
                [(f"{lignes['total']} employés", f"Données fictives d'IBM ; {pourcentage(meta['taux_depart'])} "
                                                 "sont partis.")],
                [(f"{lignes['entrainement']} pour apprendre", "Le modèle y apprend les liens entre profil et départ."),
                 (f"{lignes['test']} pour tester", "Mis de côté : le modèle ne les voit jamais en apprenant.")],
                [(f"Précision mesurée {pourcentage(precision)}", f"Sur les employés de test. Au hasard : {hasard}.")],
            ]),
        ]

        Tuile(self, "Précision (exactitude équilibrée)", pourcentage(precision),
              f"Sur 100 employés (50 partis, 50 restés), le modèle en classe correctement environ "
              f"{precision * 100:.0f}. Au hasard : {hasard}.", ACCENT).pack(fill="x", padx=4, pady=(0, 10))
        self._carte_graphique = CarteGraphique(self, list(self.GRAPHIQUES), self._choisir_graphique)
        # La page défile : le graphique reçoit une hauteur fixe au lieu de remplir la fenêtre.
        self._carte_graphique.zone.configure(height=380)
        self._carte_graphique.zone.pack_propagate(False)
        self._carte_graphique.pack(fill="x", padx=4, pady=(0, 10))
        self._graphique = next(iter(self.GRAPHIQUES.values()))
        self._afficher_graphique()

        departs_test = sum(meta["matrice_confusion"][1])
        self._carte_texte("Limites", f"• Seulement {departs_test} départs parmi les employés de test : la "
                                     "précision peut varier d'environ 3 points.\n"
                                     "• Données fictives et modèle simple : il se trompe pour environ un "
                                     "employé sur quatre.")
        self._construire_details()
        self._carte_texte("Raccourcis clavier", "Entrée : prédire · Ctrl+Suppr : vider le formulaire · "
                                                "Ctrl+1 à Ctrl+3 : changer de page · Ctrl+T : thème clair ou sombre.")
        texte_long(self, "Données : « IBM HR Analytics Employee Attrition & Performance », Kaggle (pavansubhasht), "
                         "licences Open Database License (base) et Database Contents License (contenu).\n"
                         "Maxime Hamrioui et Alexandre Bertrand-Beaudet — INF1007, automne 2026.", 11,
                   TEXTE_DISCRET, conteneur=self, marge=30).pack(anchor="w", fill="x", padx=8, pady=(6, 10))

    # ----- Construction ---------------------------------------------------------------

    def _carte(self, titre: str) -> Carte:
        """Carte pleine largeur avec son titre."""
        carte = Carte(self)
        carte.pack(fill="x", padx=4, pady=(0, 10))
        ctk.CTkLabel(carte, text=titre, font=police(16, True), text_color=TEXTE).pack(anchor="w", padx=20,
                                                                                      pady=(14, 2))
        return carte

    def _carte_texte(self, titre: str, texte: str) -> None:
        """Carte qui contient seulement un titre et un paragraphe."""
        carte = self._carte(titre)
        texte_long(carte, texte, 13, conteneur=carte, marge=50).pack(anchor="w", fill="x", padx=20, pady=(0, 16))

    def _carte_schema(self, titre: str, etapes: list[list[Boite]]) -> Schema:
        """Carte qui contient un schéma ; renvoie le schéma (à redessiner au changement de thème)."""
        schema = Schema(self._carte(titre), etapes)
        schema.pack(fill="x", padx=20, pady=(10, 18))
        return schema

    def _construire_details(self) -> None:
        """Section « Détails techniques », fermée au départ : tableau des modèles et définitions."""
        meta = self._meta
        retenu = meta["metriques_test"][meta["modele"]]
        reference = meta["metriques_test"]["Référence (classe majoritaire)"]
        carte = Carte(self)
        carte.pack(fill="x", padx=4, pady=(0, 10))
        self._bouton_details = ctk.CTkButton(carte, text="", command=self.basculer_details, anchor="w", height=40,
                                             corner_radius=10, fg_color="transparent", hover_color=SURVOL,
                                             text_color=TEXTE, font=police(16, True))
        self._bouton_details.pack(fill="x", padx=8, pady=8)
        self._details = ctk.CTkFrame(carte, fg_color="transparent")
        self._details_ouverts = False
        self._maj_bouton_details()

        etiquette_titre(self._details, "Comparaison des modèles (jeu de test)").pack(anchor="w", padx=12, pady=(0, 6))
        echelle = ctk.ScalingTracker.get_widget_scaling(self)
        colonnes = {"modele": ("Modèle", 170), "equilibree": ("Précision", 72), "validation": ("Valid. cr.", 72),
                    "exactitude": ("Exactitude", 72), "auc": ("AUC", 48)}
        self._tableau = ttk.Treeview(self._details, columns=list(colonnes), show="headings", height=2,
                                     selectmode="none", style="Theme.Treeview")
        for cle, (titre, largeur) in colonnes.items():
            self._tableau.heading(cle, text=titre)
            self._tableau.column(cle, width=int(largeur * echelle), anchor="w" if cle == "modele" else "center")
        self._colorer_tableau()
        for nom, resultats in meta["metriques_test"].items():
            self._tableau.insert("", "end", tags=("retenu",) if nom == meta["modele"] else (), values=(
                nom, pourcentage(resultats["exactitude_equilibree"]), pourcentage(meta["validation_croisee"][nom]),
                pourcentage(resultats["exactitude"]), self._decimal(resultats.get("auc", 0.5))))
        self._tableau.pack(fill="x", padx=12)

        definitions = [
            ("AUC", f"{self._decimal(retenu.get('auc', 0.5))} : chance qu'un employé parti reçoive un score plus "
                    "haut qu'un employé resté (hasard : 0,50)."),
            ("Validation croisée", f"{pourcentage(meta['validation_croisee'][meta['modele']])} : la même mesure, "
                                   f"faite avant le test sur les {meta['lignes']['entrainement']} employés "
                                   "d'entraînement (5 essais). Elle a servi à comparer le modèle à la référence."),
            ("Précision = exactitude équilibrée", "C'est la moyenne entre la part des départs bien détectés et "
             "celle des maintiens bien détectés : répondre toujours la même chose donne 50 %. L'exactitude simple "
             f"serait trompeuse : répondre toujours « reste » donne déjà {pourcentage(reference['exactitude'])}."),
            ("Calcul de la fiabilité", "Les champs vides sont remplacés par la moyenne des risques obtenus avec "
             "des employés de référence, et la précision ainsi obtenue sur les employés de test, avec les mêmes "
             f"champs remplis, donne le niveau : Faible sous {pourcentage(SEUIL_FIABILITE_MOYENNE)}, Bonne à partir "
             f"de {pourcentage(SEUIL_FIABILITE_BONNE)}, Moyenne entre les deux."),
        ]
        for titre, texte in definitions:
            etiquette_titre(self._details, titre).pack(anchor="w", padx=12, pady=(16, 2))
            texte_long(self._details, texte, 12, conteneur=carte, marge=70).pack(anchor="w", fill="x", padx=12)

    @staticmethod
    def _decimal(valeur: float) -> str:
        """0.8125 -> « 0,81 » (virgule décimale)."""
        return f"{valeur:.2f}".replace(".", ",")

    # ----- Réactions ------------------------------------------------------------------

    def basculer_details(self) -> None:
        """Ouvre ou ferme la section « Détails techniques »."""
        self._details_ouverts = not self._details_ouverts
        if self._details_ouverts:
            self._details.pack(fill="x", padx=12, pady=(0, 16), after=self._bouton_details)
        else:
            self._details.pack_forget()
        self._maj_bouton_details()

    def _maj_bouton_details(self) -> None:
        """Flèche ▸ (fermé) ou ▾ (ouvert) devant le titre de la section."""
        self._bouton_details.configure(text=f"{'▾' if self._details_ouverts else '▸'}   Détails techniques")

    def _colorer_tableau(self) -> None:
        """Le modèle retenu est écrit dans la couleur d'accent du thème actif."""
        self._tableau.tag_configure("retenu", foreground=couleur(ACCENT))

    def _choisir_graphique(self, choix: str) -> None:
        """Appelé par le sélecteur de graphique."""
        self._graphique = self.GRAPHIQUES[choix]
        self._afficher_graphique()

    def _afficher_graphique(self) -> None:
        """Dessine le graphique d'évaluation choisi et son mode d'emploi."""
        meta, theme = self._meta, theme_graphique()
        if self._graphique == "matrice":
            figure = figure_matrice_confusion(meta["matrice_confusion"], theme=theme)
            lecture = ("Chaque case compte des employés du test : en vert, le modèle a vu juste ; en rouge, il "
                       "s'est trompé. Il préfère lancer une fausse alerte plutôt que de rater un départ.")
        else:
            figure = figure_importances(meta["importances"], theme=theme)
            lecture = ("Plus la barre est longue, plus le modèle a besoin de cette information. C'est aussi "
                       "l'ordre des champs conseillés dans le formulaire.")
        self._carte_graphique.zone.afficher(figure)
        self._carte_graphique.expliquer(lecture)

    def changer_theme(self) -> None:
        """Redessine les schémas et le graphique, recolore le tableau."""
        for schema in self._schemas:
            schema.dessiner()
        self._colorer_tableau()
        self._afficher_graphique()


class PageHistorique(ctk.CTkFrame):
    """Tableau des prédictions passées et détail de la ligne sélectionnée."""

    def __init__(self, parent: ctk.CTkBaseClass, application: Application,
                 recharger: Callable[[dict[str, str]], None]) -> None:
        """recharger reçoit les saisies d'une ligne pour les remettre dans le formulaire."""
        super().__init__(parent, fg_color="transparent")
        self._application = application
        self._recharger = recharger
        self._lignes: dict[str, dict[str, str]] = {}
        self.columnconfigure(0, weight=3, uniform="colonnes")
        self.columnconfigure(1, weight=2, uniform="colonnes")
        self.rowconfigure(1, weight=1)

        haut = ctk.CTkFrame(self, fg_color="transparent")
        haut.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        haut.columnconfigure(0, weight=1)
        ctk.CTkLabel(haut, text="Historique", font=police(26, True), text_color=TEXTE).grid(row=0, column=0,
                                                                                         sticky="w")
        self._compte = texte_long(haut, "", 13, conteneur=haut, marge=330)
        self._compte.grid(row=1, column=0, sticky="w")
        bouton_secondaire(haut, "Rafraîchir", self.rafraichir, width=120).grid(row=0, column=1, rowspan=2, padx=8)
        bouton_secondaire(haut, "Effacer l'historique", self._effacer, couleur_texte=ERREUR, width=170).grid(
            row=0, column=2, rowspan=2)

        carte = Carte(self)
        carte.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        echelle = ctk.ScalingTracker.get_widget_scaling(self)
        colonnes = {"date": ("Date", 150), "risque": ("Risque", 70), "conclusion": ("Conclusion", 130),
                    "champs": ("Champs", 64), "fiabilite": ("Fiabilité", 76)}
        self._tableau = ttk.Treeview(carte, columns=list(colonnes), show="headings", selectmode="browse",
                                     style="Theme.Treeview")
        for cle, (titre, largeur) in colonnes.items():
            self._tableau.heading(cle, text=titre)
            self._tableau.column(cle, width=int(largeur * echelle), anchor="w" if cle == "date" else "center")
        barre = ctk.CTkScrollbar(carte, command=self._tableau.yview, button_color=BORDURE,
                                 button_hover_color=SURVOL)
        self._tableau.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y", padx=(0, 6), pady=10)
        self._tableau.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self._tableau.bind("<<TreeviewSelect>>", self._afficher_detail)
        self._tableau.bind("<Double-1>", lambda _: self._recharger_selection())

        detail = Carte(self)
        detail.grid(row=1, column=1, sticky="nsew")
        etiquette_titre(detail, "Saisies de la prédiction sélectionnée").pack(anchor="w", padx=18, pady=(16, 6))
        self._bouton_recharger = bouton_principal(detail, "Recharger dans le formulaire", self._recharger_selection,
                                                  height=36, font=police(13, True), state="disabled")
        self._bouton_recharger.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        self._detail = ctk.CTkTextbox(detail, fg_color=CARTE, text_color=TEXTE, font=police(13), wrap="word",
                                      activate_scrollbars=True, scrollbar_button_color=BORDURE)
        self._detail.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.rafraichir()

    def rafraichir(self) -> None:
        """Relit le fichier d'historique et remplit le tableau."""
        try:
            lignes = self._application.historique.lire()
        except (DonneeInvalideError, OSError) as erreur:
            self._compte.configure(text=f"Historique illisible : {erreur}", text_color=ERREUR)
            return
        self._tableau.tag_configure("impaire", background=couleur(CARTE_RELIEF))
        self._tableau.tag_configure("depart", foreground=couleur(NIVEAUX["élevé"][0]))
        self._tableau.tag_configure("maintien", foreground=couleur(NIVEAUX["faible"][0]))
        self._tableau.delete(*self._tableau.get_children())
        self._lignes.clear()
        for rang, ligne in enumerate(lignes):
            etiquettes = ["depart" if ligne["conclusion"] == "départ probable" else "maintien"]
            if rang % 2:
                etiquettes.append("impaire")
            identifiant = self._tableau.insert("", "end", tags=etiquettes, values=(
                ligne["date"].replace("T", "  "), self._format_pourcentage(ligne["risque_depart"]),
                ligne["conclusion"], ligne["champs_renseignes"], fiabilite_depuis_texte(ligne["precision_attendue"])))
            self._lignes[identifiant] = ligne
        self._compte.configure(text=f"{len(lignes)} prédiction(s) enregistrée(s) · sélectionnez une ligne pour "
                                    f"revoir ses saisies, double-cliquez pour la recharger" if lignes
                               else "Aucune prédiction pour l'instant.", text_color=TEXTE_SECONDAIRE)
        self._ecrire_detail("")
        self._bouton_recharger.configure(state="disabled")

    changer_theme = rafraichir

    @staticmethod
    def _format_pourcentage(texte: str) -> str:
        """« 0.684 » -> « 68 % » ; le texte tel quel s'il n'est pas un nombre."""
        try:
            return pourcentage(float(texte))
        except ValueError:
            return texte

    def _ligne_choisie(self) -> dict[str, str] | None:
        """Ligne de l'historique sélectionnée dans le tableau, ou None."""
        selection = self._tableau.selection()
        return self._lignes.get(selection[0]) if selection else None

    def _afficher_detail(self, _evenement=None) -> None:
        """Affiche les saisies de la ligne choisie, avec les libellés en français."""
        ligne = self._ligne_choisie()
        if ligne is None:
            return
        try:
            saisies = json.loads(ligne["saisies"])
            lignes = [f"{self._application.variable(nom).libelle} : "
                      f"{self._application.variable(nom).formater(valeur)}" for nom, valeur in saisies.items()]
        except (json.JSONDecodeError, AttributeError, DonneeInvalideError):
            lignes = [ligne["saisies"]]
        self._ecrire_detail("\n".join(lignes))
        self._bouton_recharger.configure(state="normal")

    def _recharger_selection(self) -> None:
        """Remet les saisies de la ligne choisie dans le formulaire de prédiction."""
        ligne = self._ligne_choisie()
        if ligne is None:
            return
        try:
            saisies = self._application.saisies_depuis_historique(ligne)
        except DonneeInvalideError as erreur:
            messagebox.showerror("Recharger", str(erreur), parent=self)
            return
        self._recharger(saisies)

    def _ecrire_detail(self, texte: str) -> None:
        """Remplace le contenu de la zone de détail (en lecture seule)."""
        self._detail.configure(state="normal")
        self._detail.delete("1.0", "end")
        self._detail.insert("1.0", texte)
        self._detail.configure(state="disabled")

    def _effacer(self) -> None:
        """Supprime le fichier d'historique après confirmation."""
        if not messagebox.askyesno("Effacer l'historique",
                                   "Supprimer définitivement toutes les prédictions enregistrées ?", parent=self):
            return
        try:
            self._application.historique.effacer()
        except OSError as erreur:
            messagebox.showerror("Effacer l'historique", f"Impossible de supprimer le fichier : {erreur}",
                                 parent=self)
        self.rafraichir()
