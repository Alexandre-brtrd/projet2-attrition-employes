"""Les quatre pages de la fenêtre : Prédiction, Le modèle, Historique, À propos.

Les pages n'effectuent aucun calcul : elles lisent les saisies, appellent l'Application
et affichent ce qu'elle renvoie. Chaque graphique est accompagné d'un court texte
« Comment lire ce graphique » écrit pour un non-informaticien.
"""

import json
from collections.abc import Callable
from tkinter import messagebox, ttk

import customtkinter as ctk

from frontend.application import Application, Prediction, points, pourcentage
from frontend.composants import (Carte, Champ, InfoBulle, Tuile, ZoneGraphique, bouton_principal,
                                 bouton_secondaire, etiquette_titre, pastille, selecteur, texte_long)
from frontend.graphiques import figure_effets, figure_precision_champs, figure_risque_reel, figure_vide
from frontend.theme import (ACCENT, AVERTISSEMENT, BORDURE, CARTE, CARTE_RELIEF, ERREUR, NIVEAUX, SUCCES,
                            SURVOL, TEXTE, TEXTE_DISCRET, TEXTE_SECONDAIRE, couleur, police, theme_graphique)
from backend.exceptions import DonneeInvalideError, SaisieInvalideError
from backend.graphiques import figure_comparaison_cibles, figure_importances, figure_matrice_confusion
from backend.style import libelle_court

ETAPES = ("1.  Décrivez l'employé. Un seul champ suffit ; plus il y en a, plus le résultat est fiable.\n"
          "2.  Cliquez sur « Prédire » (ou appuyez sur Entrée).\n"
          "3.  Lisez le risque, puis les graphiques ci-dessous pour comprendre d'où il vient.")


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
    """Formulaire à gauche ; risque, explications et graphiques à droite."""

    GRAPHIQUES = {"Précision": "precision", "Facteurs": "effets", "Que veut dire le % ?": "sens"}

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
        self._graphique = "precision"
        self._champs_dessines: frozenset[str] | None = None
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=11, uniform="colonnes")
        self.columnconfigure(1, weight=10, uniform="colonnes")
        self._construire_formulaire()
        self._construire_resultats()
        self.maj_indicateur()

    def adapter(self, compact: bool) -> None:
        """Fenêtre étroite : chaque saisie passe sous son libellé et le mode d'emploi des
        graphiques passe dans une bulle, pour que rien ne soit coupé."""
        for champ in self._champs.values():
            champ.adapter(compact)
        self._carte_graphique.adapter(compact)

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
                         "mais la précision attendue baisse. Survolez ⓘ pour une explication.", 13,
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
        self._message = texte_long(pied, "", 12, conteneur=pied, marge=300)
        self._message.grid(row=0, column=0, sticky="w")
        effacer = bouton_secondaire(pied, "Tout effacer", self.effacer, width=120)
        effacer.grid(row=0, column=1, padx=10)
        InfoBulle(effacer, "Vider le formulaire (Ctrl+Suppr)")
        predire = bouton_principal(pied, "Prédire  →", self.predire, width=150)
        predire.grid(row=0, column=2)
        InfoBulle(predire, "Calculer le risque (Entrée)")

    def _construire_resultats(self) -> None:
        """Colonne de droite : carte du résultat, carte des graphiques."""
        colonne = ctk.CTkFrame(self, fg_color="transparent")
        colonne.grid(row=0, column=1, sticky="nsew")
        colonne.columnconfigure(0, weight=1)

        carte = Carte(colonne)
        carte.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        carte.columnconfigure((0, 1), weight=1, uniform="indicateurs")

        risque = ctk.CTkFrame(carte, fg_color="transparent")
        risque.grid(row=0, column=0, sticky="ew", padx=(20, 12), pady=(14, 0))
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

        precision = ctk.CTkFrame(carte, fg_color="transparent")
        precision.grid(row=0, column=1, sticky="ew", padx=(12, 20), pady=(14, 0))
        titre_precision = etiquette_titre(precision, "Précision attendue  ⓘ")
        titre_precision.pack(anchor="w")
        InfoBulle(titre_precision, "Si on montrait au modèle autant d'employés partis que restés, il en "
                                   "classerait correctement ce pourcentage. Mesuré sur les employés du test, "
                                   "avec exactement les champs que vous avez remplis. 50 % = hasard.")
        self._precision = ctk.CTkLabel(precision, text="50 %", font=police(38, True), text_color=ACCENT, height=46)
        self._precision.pack(anchor="w")
        self._nb_champs = ctk.CTkLabel(precision, text="", font=police(12), text_color=TEXTE_SECONDAIRE, height=26)
        self._nb_champs.pack(anchor="w", pady=(0, 6))
        self._barre_champs = ctk.CTkProgressBar(precision, height=8, corner_radius=4, fg_color=SURVOL,
                                                progress_color=ACCENT)
        self._barre_champs.pack(fill="x")

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
        """Champs remplis par section, précision attendue, conseils et graphique de précision."""
        self._minuterie = None
        saisies = self._saisies()
        champs = self._application.champs_renseignes(saisies)
        total = len(self._champs)
        self._precision.configure(text=pourcentage(self._application.precision_attendue(champs)))
        self._nb_champs.configure(text=f"{len(champs)} / {total} champs remplis")
        self._barre_champs.set(len(champs) / total)
        for groupe, (remplis, nombre) in self._application.progression_par_groupe(saisies).items():
            self._progression[groupe].configure(
                text=f"{remplis} / {nombre}" + ("  ✓" if remplis == nombre else ""),
                text_color=SUCCES if remplis == nombre else ACCENT if remplis else TEXTE_DISCRET)
        self._afficher_conseils(champs)
        if self._prediction is not None and saisies != self._saisies_predites:
            self._perime.pack(anchor="w", fill="x", after=self._phrase, pady=(4, 0))
        else:
            self._perime.pack_forget()
        if self._graphique == "precision" and frozenset(champs) != self._champs_dessines:
            self._afficher_graphique()

    def _afficher_conseils(self, champs: list[str]) -> None:
        """Pastilles cliquables : les champs vides les plus utiles à remplir ensuite."""
        for enfant in self._conseils.winfo_children():
            enfant.destroy()
        conseilles = self._application.champs_conseilles(champs)
        if not conseilles:
            ctk.CTkLabel(self._conseils, text="Tous les champs sont remplis.", font=police(12),
                         text_color=SUCCES).pack(side="left")
            return
        ctk.CTkLabel(self._conseils, text="Pour gagner en précision, remplissez :", font=police(12),
                     text_color=TEXTE_SECONDAIRE).pack(side="left", padx=(0, 6))
        for variable in conseilles:
            pastille(self._conseils, libelle_court(variable.nom),
                     lambda nom=variable.nom: self._defiler_vers(self._champs[nom])).pack(side="left", padx=2)

    def _choisir_graphique(self, choix: str) -> None:
        """Appelé par le sélecteur de graphique."""
        self._graphique = self.GRAPHIQUES[choix]
        self._afficher_graphique()

    def _afficher_graphique(self) -> None:
        """Dessine le graphique choisi et son mode d'emploi."""
        theme = theme_graphique()
        champs = self._application.champs_renseignes(self._saisies())
        meta = self._application.metadonnees
        nb_test = meta.get("lignes", {}).get("test", "les")
        if self._graphique == "precision":
            self._champs_dessines = frozenset(champs)
            ordre = meta["courbe_precision"].get("ordre", [])
            figure = figure_precision_champs(meta["courbe_precision"], len(champs),
                                             self._application.precision_attendue(champs), theme=theme,
                                             premier_champ=libelle_court(ordre[0]) if ordre else None)
            lecture = (f"Chaque point est mesuré sur {nb_test} employés que le modèle n'a jamais vus. La ligne "
                       "bleue montre la précision quand on remplit d'abord les champs les plus utiles ; la ligne "
                       "orange, quand on les remplit au hasard. Le gros point représente votre formulaire. "
                       "Remplir les champs proposés au-dessus le fait monter le plus vite.")
        elif self._graphique == "effets":
            if self._prediction is None:
                figure = figure_vide("Cliquez sur « Prédire » pour voir ce qui influence le résultat.", theme)
            else:
                valeurs = {nom: self._application.variable(nom).formater(valeur)
                           for nom, valeur in self._prediction.valeurs_connues.items()}
                figure = figure_effets(self._prediction.effets, valeurs, theme=theme)
            lecture = ("Pour chaque information saisie, on recalcule le risque comme si ce champ était resté "
                       "vide. La barre montre l'écart, en points de pourcentage : rouge, l'information fait "
                       "monter le risque ; verte, elle le fait baisser. Les écarts ne s'additionnent pas "
                       "exactement, car les informations interagissent.")
        else:
            connus = self._prediction.valeurs_connues if self._prediction else champs
            figure = figure_risque_reel(self._application.tranches_de_risque(connus),
                                        self._prediction.probabilite if self._prediction else None, theme=theme)
            lecture = ("Le pourcentage affiché est un score de risque, pas une probabilité exacte : pendant "
                       "l'entraînement, les départs (16 % des employés) ont reçu autant de poids que les "
                       "maintiens. Ce graphique le traduit en faits : on a calculé le score des employés du "
                       "test avec les mêmes champs que vous, puis compté combien sont vraiment partis dans "
                       "chaque tranche.")
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
        """Risque, badge coloré, phrases en langage courant et facteurs principaux."""
        couleur_niveau, fond = NIVEAUX[prediction.niveau]
        self._risque.configure(text=pourcentage(prediction.probabilite), text_color=couleur_niveau)
        self._badge.configure(text=f"   Risque {prediction.niveau}   ",
                              fg_color=fond, text_color=couleur_niveau)
        self._barre_risque.configure(progress_color=couleur_niveau)
        self._barre_risque.set(prediction.probabilite)

        position = self._application.situer(prediction)
        tranche = position["tranche"]
        phrase = (f"Le modèle prévoit un {prediction.conclusion()}. Ce score dépasse celui de "
                  f"{pourcentage(position['depasse'])} des employés du test.")
        if tranche["employes"]:
            phrase += (f" Parmi les employés du test au score semblable ({tranche['bas'] * 100:.0f} à "
                       f"{tranche['haut'] * 100:.0f} %), {tranche['partis']} sur {tranche['employes']} sont "
                       f"vraiment partis ({pourcentage(tranche['partis'] / tranche['employes'])}).")
        phrase += (f" Avec {prediction.nb_champs} champ(s) rempli(s) sur {prediction.nb_variables}, le modèle "
                   f"classe correctement environ {pourcentage(prediction.precision_attendue)} des employés "
                   "(50 % = hasard).")
        self._phrase.configure(text=phrase)
        self._afficher_facteurs(prediction)
        self.maj_indicateur()
        if self._graphique != "precision":
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
        if self._graphique != "precision":
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


class PageModele(ctk.CTkFrame):
    """Indicateurs clés, comparaison des modèles, explications et graphiques d'évaluation."""

    GRAPHIQUES = {"Bonnes et mauvaises réponses": "matrice", "Variables utiles": "importances",
                  "Pourquoi pas la satisfaction ?": "cibles"}

    def __init__(self, parent: ctk.CTkBaseClass, application: Application) -> None:
        super().__init__(parent, fg_color="transparent")
        self._meta = application.metadonnees
        meta = self._meta
        retenu = meta["metriques_test"][meta["modele"]]
        reference = meta["metriques_test"]["Référence (classe majoritaire)"]
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        entete(self, f"Le modèle : {meta['modele'].lower()}",
               f"Choisi par validation croisée sur {meta['lignes']['entrainement']} employés d'entraînement, "
               f"puis évalué une seule fois sur {meta['lignes']['test']} employés de test qu'il n'avait jamais "
               f"vus. Entraîné le {meta['date_entrainement'].replace('T', ' à ')} en "
               f"{meta['duree_entrainement_s']:.2f} s.").grid(row=0, column=0, sticky="ew", pady=(0, 14))

        tuiles = ctk.CTkFrame(self, fg_color="transparent")
        tuiles.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        detectes = meta["matrice_confusion"][1][1]
        departs_test = sum(meta["matrice_confusion"][1])
        precision = retenu["exactitude_equilibree"]
        donnees_tuiles = [
            ("Précision (exactitude équilibrée)", pourcentage(precision),
             f"Sur 100 départs et 100 maintiens, environ {precision * 100:.0f} bien classés. Hasard : "
             f"{pourcentage(reference['exactitude_equilibree'])}.", ACCENT),
            ("Validation croisée", pourcentage(meta["validation_croisee"][meta["modele"]]),
             "Même mesure, faite avant le test sur l'entraînement (5 essais).", TEXTE),
            ("AUC", f"{retenu.get('auc', 0.5):.2f}".replace(".", ","),
             "Chance qu'un employé parti ait un score plus haut qu'un employé resté (hasard : 0,50).", TEXTE),
            ("Départs détectés", f"{detectes} sur {departs_test}",
             f"Soit {pourcentage(retenu['rappel_depart'])} des départs du test.", TEXTE),
        ]
        for colonne, (titre, valeur, detail, teinte) in enumerate(donnees_tuiles):
            tuiles.columnconfigure(colonne, weight=1, uniform="tuiles")
            Tuile(tuiles, titre, valeur, detail, teinte).grid(row=0, column=colonne, sticky="nsew",
                                                              padx=(0 if colonne == 0 else 6, 0))

        bas = ctk.CTkFrame(self, fg_color="transparent")
        bas.grid(row=2, column=0, sticky="nsew")
        bas.columnconfigure(0, weight=5, uniform="bas")
        bas.columnconfigure(1, weight=6, uniform="bas")
        bas.rowconfigure(0, weight=1)
        self._construire_details(bas)

        self._carte_graphique = CarteGraphique(bas, list(self.GRAPHIQUES), self._choisir_graphique)
        self._carte_graphique.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        self._graphique = next(iter(self.GRAPHIQUES.values()))
        self._afficher_graphique()

    def _construire_details(self, parent: ctk.CTkFrame) -> None:
        """Carte de gauche : tableau comparatif, définitions, limites, nettoyage."""
        meta = self._meta
        carte = Carte(parent)
        carte.grid(row=0, column=0, sticky="nsew")
        zone = ctk.CTkScrollableFrame(carte, fg_color=CARTE, scrollbar_button_color=BORDURE,
                                      scrollbar_button_hover_color=SURVOL)
        zone.pack(fill="both", expand=True, padx=6, pady=6)
        etiquette_titre(zone, "Comparaison des modèles (jeu de test)").pack(anchor="w", padx=12, pady=(10, 6))
        echelle = ctk.ScalingTracker.get_widget_scaling(self)
        colonnes = {"modele": ("Modèle", 170), "equilibree": ("Précision", 72), "validation": ("Valid. cr.", 72),
                    "exactitude": ("Exactitude", 72), "auc": ("AUC", 48)}
        self._tableau = ttk.Treeview(zone, columns=list(colonnes), show="headings", height=3, selectmode="none",
                                     style="Theme.Treeview")
        for cle, (titre, largeur) in colonnes.items():
            self._tableau.heading(cle, text=titre)
            self._tableau.column(cle, width=int(largeur * echelle), anchor="w" if cle == "modele" else "center")
        self._colorer_tableau()
        for nom, resultats in meta["metriques_test"].items():
            self._tableau.insert("", "end", tags=("retenu",) if nom == meta["modele"] else (), values=(
                nom, pourcentage(resultats["exactitude_equilibree"]), pourcentage(meta["validation_croisee"][nom]),
                pourcentage(resultats["exactitude"]), f"{resultats.get('auc', 0.5):.2f}".replace(".", ",")))
        self._tableau.pack(fill="x", padx=12)

        satisfaction = meta["comparaison_cibles"]["Satisfaction (≥ 3 sur 4)"]
        sections = [
            ("Pourquoi « précision » et pas « exactitude » ?", "La précision affichée partout est l'exactitude "
             "équilibrée : la moyenne entre la part des départs bien détectés et celle des maintiens bien "
             "détectés. Répondre toujours la même chose donne 50 %. L'exactitude simple est trompeuse ici : "
             f"répondre toujours « reste » donne déjà "
             f"{pourcentage(meta['metriques_test']['Référence (classe majoritaire)']['exactitude'])}, "
             "sans détecter un seul départ."),
            ("Pourquoi pas la satisfaction ?", "Prédire si un employé est satisfait (3 ou 4 sur 4) donne "
             + " et ".join(f"{pourcentage(valeur)} ({nom.lower()})" for nom, valeur in satisfaction.items())
             + " : aucun modèle ne fait mieux que le hasard. Le départ, lui, est prévisible."),
            ("Limites", f"Seulement {sum(meta['matrice_confusion'][1])} départs dans le jeu de test (environ "
             "± 3 points d'incertitude), données fictives, modèle linéaire : il se trompe pour environ un "
             "employé sur quatre."),
            ("Nettoyage des données", "\n".join(f"• {etape}" for etape in meta["nettoyage"])),
        ]
        for titre, texte in sections:
            etiquette_titre(zone, titre).pack(anchor="w", padx=12, pady=(16, 2))
            texte_long(zone, texte, 12, conteneur=carte, marge=70).pack(anchor="w", fill="x", padx=12)

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
            (_, fausses_alertes), (manques, _) = meta["matrice_confusion"]
            figure = figure_matrice_confusion(meta["matrice_confusion"], theme=theme)
            lecture = ("Chaque case compte des employés du test. Vert : le modèle a vu juste ; rouge : il s'est "
                       f"trompé. Il lance {fausses_alertes} fausses alertes pour {manques} départs manqués : "
                       "c'est voulu. Les départs ont reçu plus de poids à l'entraînement, pour que le modèle "
                       "préfère signaler un départ de trop plutôt que d'en rater un.")
        elif self._graphique == "importances":
            figure = figure_importances(meta["importances"], theme=theme)
            lecture = ("On mélange au hasard une colonne à la fois et on mesure la précision perdue. Plus la "
                       "barre est longue, plus le modèle a besoin de cette information. C'est aussi l'ordre des "
                       "champs conseillés dans le formulaire.")
        else:
            figure = figure_comparaison_cibles(meta["comparaison_cibles"], theme=theme)
            lecture = ("Nous voulions d'abord prédire la satisfaction au travail. Avec les mêmes données, le "
                       "modèle fait moins bien que le hasard (barre sous la ligne pointillée). Le départ, lui, "
                       "est prévisible : c'est pour cela que l'application prédit le départ.")
        self._carte_graphique.zone.afficher(figure)
        self._carte_graphique.expliquer(lecture)

    def changer_theme(self) -> None:
        """Redessine le graphique et recolore le tableau."""
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
        self._compte = ctk.CTkLabel(haut, text="", font=police(13), text_color=TEXTE_SECONDAIRE)
        self._compte.grid(row=1, column=0, sticky="w")
        bouton_secondaire(haut, "Rafraîchir", self.rafraichir, width=120).grid(row=0, column=1, rowspan=2, padx=8)
        bouton_secondaire(haut, "Effacer l'historique", self._effacer, couleur_texte=ERREUR, width=170).grid(
            row=0, column=2, rowspan=2)

        carte = Carte(self)
        carte.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        echelle = ctk.ScalingTracker.get_widget_scaling(self)
        colonnes = {"date": ("Date", 150), "risque": ("Risque", 70), "conclusion": ("Conclusion", 130),
                    "champs": ("Champs", 64), "precision": ("Précision", 76)}
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
                ligne["conclusion"], ligne["champs_renseignes"], self._format_pourcentage(ligne["precision_attendue"])))
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


class PageAPropos(ctk.CTkScrollableFrame):
    """Explications pour l'utilisateur, une carte par question."""

    SECTIONS = [
        ("Que fait cette application ?",
         "Elle estime le risque qu'un employé quitte son entreprise à partir de 26 caractéristiques de sa vie "
         "professionnelle et personnelle : âge, état civil, poste, salaire, heures supplémentaires, ancienneté, "
         "satisfaction, équilibre travail-vie personnelle, etc."),
        ("Comment lire le « risque de départ » ?",
         "Pendant l'entraînement, le modèle accorde autant de poids aux départs (16 % des employés) qu'aux "
         "maintiens, pour ne pas se contenter de répondre toujours « reste ». Le pourcentage affiché est donc "
         "un score de risque plutôt qu'une probabilité : au-delà de 50 %, le modèle conclut à un départ "
         "probable. Le graphique « Que veut dire le % ? » de la page Prédiction le traduit en faits : parmi les "
         "employés du test qui ont reçu un score semblable, combien sont vraiment partis."),
        ("Comment est calculée la « précision attendue » ?",
         "Quand un champ est vide, on ne connaît pas sa valeur : le modèle essaie les valeurs de 40 vrais "
         "employés de référence et fait la moyenne des risques obtenus. Le même calcul est appliqué aux employés "
         "du jeu de test (jamais vus à l'entraînement) en ne gardant que les champs que vous avez remplis. La "
         "précision attendue est l'exactitude équilibrée obtenue : la moyenne entre le pourcentage de départs "
         "bien détectés et celui des maintiens bien détectés. 50 % correspond au hasard. Le jeu de test ne "
         "contient que 59 départs : ce pourcentage varie d'environ ± 3 points selon l'échantillon."),
        ("Pourquoi ne pas prédire directement la satisfaction ?",
         "Nous l'avons essayé : la satisfaction au travail n'a presque aucun lien avec les autres variables de "
         "ce jeu de données (corrélations inférieures à 0,11). Le meilleur modèle faisait moins bien que la "
         "référence triviale (voir la page « Le modèle »). Le départ, lui, est l'expression mesurable du "
         "contentement, et il est prévisible."),
        ("Raccourcis clavier",
         "Entrée : prédire · Ctrl+Suppr : vider le formulaire · Ctrl+1 à Ctrl+4 : changer de page · "
         "Ctrl+T : passer du thème clair au thème sombre."),
        ("Source des données",
         "« IBM HR Analytics Employee Attrition & Performance », Kaggle (pavansubhasht), licence Open Database "
         "License (base) et Database Contents License (contenu). 1470 employés fictifs, 35 colonnes."),
        ("Auteurs", "Maxime Hamrioui et Alexandre Bertrand-Beaudet — INF1007, automne 2026."),
    ]

    def __init__(self, parent: ctk.CTkBaseClass) -> None:
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=BORDURE,
                         scrollbar_button_hover_color=SURVOL)
        entete(self, "À propos", "Ce que fait l'application, ses limites et la façon de lire ses résultats.").pack(
            anchor="w", fill="x", padx=4, pady=(0, 14))
        for titre, texte in self.SECTIONS:
            carte = Carte(self)
            carte.pack(fill="x", padx=4, pady=(0, 10))
            ctk.CTkLabel(carte, text=titre, font=police(16, True), text_color=TEXTE).pack(anchor="w", padx=20,
                                                                                          pady=(14, 2))
            texte_long(carte, texte, 13, conteneur=carte, marge=50).pack(anchor="w", fill="x", padx=20,
                                                                         pady=(0, 16))

    def changer_theme(self) -> None:
        """Rien à redessiner : CustomTkinter recolore lui-même les cartes."""
