"""Tests de bout en bout de l'interface : la vraie fenêtre, pilotée comme le ferait un utilisateur.

Ils ouvrent la fenêtre CustomTkinter avec le modèle sauvegardé (backend/sauvegarde/) et un
historique temporaire. Sans écran (ex. GitHub Actions), ils sont ignorés : les autres tests
couvrent la logique, que l'interface ne fait qu'appeler.
"""

import time
import tkinter

import pytest

try:
    _racine = tkinter.Tk()
    _racine.destroy()
except tkinter.TclError:
    pytest.skip("pas d'écran disponible pour ouvrir une fenêtre", allow_module_level=True)

from frontend.application import Application
from frontend.fenetre import FenetrePrincipale
from frontend.theme import mode_sombre


def attendre(fenetre: FenetrePrincipale, millisecondes: int) -> None:
    """Laisse tourner la boucle Tkinter (minuteries, redessins) pendant ce temps."""
    fin = time.monotonic() + millisecondes / 1000
    while time.monotonic() < fin:
        fenetre.update()
        time.sleep(0.02)


def attendre_que(fenetre: FenetrePrincipale, condition, delai_ms: int = 4000) -> bool:
    """Laisse tourner la boucle Tkinter jusqu'à ce que condition() soit vraie (ou jusqu'au délai)."""
    fin = time.monotonic() + delai_ms / 1000
    while time.monotonic() < fin:
        fenetre.update()
        if condition():
            return True
        time.sleep(0.02)
    return bool(condition())


@pytest.fixture(scope="module")
def fenetre(tmp_path_factory):
    """Fenêtre complète, ouverte une fois pour tout le fichier."""
    historique = str(tmp_path_factory.mktemp("interface") / "historique.csv")
    fenetre = FenetrePrincipale()
    fenetre.geometry("1500x930+0+0")
    fenetre.installer(Application.depuis_fichiers(chemin_historique=historique))
    # Au premier plan : sans cela, Windows ne signale pas qu'un champ perd le focus.
    fenetre.attributes("-topmost", True)
    fenetre.focus_force()
    attendre(fenetre, 500)
    yield fenetre
    fenetre.destroy()


@pytest.fixture
def page(fenetre):
    """Page Prédiction, formulaire vide, affichée."""
    fenetre.afficher_page("prediction")
    prediction = fenetre._pages["prediction"]
    prediction.effacer()
    attendre(fenetre, 100)
    return prediction


def taper(fenetre, champ, texte: str) -> None:
    """Tape texte caractère par caractère, en laissant le temps au graphique de se redessiner."""
    for caractere in texte:
        champ.widget.insert("end", caractere)  # CTkEntry.insert retire d'abord l'exemple grisé
        champ.widget._entry.event_generate("<KeyRelease>")
        attendre(fenetre, 400)  # plus que les 250 ms avant le recalcul de la précision


def test_le_curseur_reste_dans_le_champ_pendant_la_saisie(fenetre, page):
    """Régression : le graphique redessiné volait le curseur, et « 49 » (pour 4988) était refusé."""
    champ = page._champs["MonthlyIncome"]
    champ.donner_focus()
    attendre(fenetre, 100)
    taper(fenetre, champ, "49")
    assert fenetre.focus_lastfor() is champ.widget._entry
    assert not champ._message.winfo_manager() == "grid"
    taper(fenetre, champ, "88")
    assert champ.texte() == "4988"
    assert champ.verifier()


def test_quitter_un_champ_invalide_affiche_l_erreur(fenetre, page):
    champ = page._champs["Age"]
    champ.donner_focus()
    taper(fenetre, champ, "7")
    page._champs["MonthlyIncome"].donner_focus()  # l'utilisateur passe au champ suivant
    # Windows n'envoie FocusOut qu'à une fenêtre au premier plan, ce que pytest ne garantit pas.
    champ.widget._entry.event_generate("<FocusOut>")
    attendre(fenetre, 300)
    assert champ._message.winfo_manager() == "grid"
    assert "entre 18 et 60" in champ._message.cget("text")


def test_prediction_d_un_vrai_employe(fenetre, page):
    nb_avant = len(fenetre._pages["historique"]._lignes)
    page._charger_exemple("risque")
    page.predire()
    attendre(fenetre, 200)
    assert page._risque.cget("text").endswith("%")
    assert "départ probable" in page._phrase.cget("text")
    assert len(page._facteurs.winfo_children()) > 1  # titre + facteurs principaux
    assert len(fenetre._pages["historique"]._lignes) == nb_avant + 1


def test_saisie_invalide_un_message_et_pas_de_plantage(fenetre, page):
    page._champs["Age"].definir("abc")
    page._champs["MonthlyIncome"].definir("50")
    page.predire()
    attendre(fenetre, 100)
    assert "2 saisie(s) à corriger" in page._message.cget("text")
    assert page._champs["Age"]._message.winfo_manager() == "grid"
    assert page._risque.cget("text") == "—"


def test_formulaire_vide(fenetre, page):
    page.predire()
    assert "Aucun champ renseigné" in page._message.cget("text")


def test_boutons_de_choix(fenetre, page):
    heures = page._champs["OverTime"]
    heures.definir("Oui")
    assert heures.texte() == "Oui"
    satisfaction = page._champs["JobSatisfaction"]
    satisfaction.definir("3 — Élevée")
    assert satisfaction._segments.get() == "Élevée"
    satisfaction.effacer()
    assert satisfaction.texte() == ""


def test_progression_et_conseils(fenetre, page):
    page._champs["OverTime"].definir("Oui")
    page.maj_indicateur()
    assert page._progression["Poste"].cget("text").startswith("1 / 5")
    conseils = [enfant.cget("text") for enfant in page._conseils.winfo_children()]
    assert "Heures supplémentaires" not in conseils  # déjà rempli : on conseille les suivants
    assert len(conseils) == 4  # la phrase et trois pastilles


@pytest.mark.parametrize("choix", ["Précision", "Facteurs", "Que veut dire le % ?"])
def test_chaque_graphique_se_dessine(fenetre, page, choix):
    page._charger_exemple("stable")
    page.predire()
    page._choisir_graphique(choix)
    attendre(fenetre, 100)
    assert page._carte_graphique.zone._canevas is not None
    assert page._carte_graphique._lecture.cget("text")


def test_changer_de_theme(fenetre, page):
    sombre = mode_sombre()
    fenetre.changer_theme()
    attendre(fenetre, 200)
    assert mode_sombre() is not sombre
    fenetre.changer_theme()
    assert mode_sombre() is sombre


def test_raccourcis_clavier(fenetre, page):
    # La touche est envoyée à un champ : comme dans la vraie vie, elle remonte jusqu'à la fenêtre.
    entree = page._champs["Age"].widget._entry
    entree.event_generate("<Control-Key-2>")
    assert attendre_que(fenetre, lambda: fenetre._page_active == "modele")
    entree.event_generate("<Control-Key-1>")
    assert attendre_que(fenetre, lambda: fenetre._page_active == "prediction")


def test_recharger_une_prediction_de_l_historique(fenetre, page):
    page._champs["Age"].definir("41")
    page._champs["OverTime"].definir("Non")
    page.predire()
    page.effacer()
    fenetre.afficher_page("historique")
    historique = fenetre._pages["historique"]
    historique._tableau.selection_set(historique._tableau.get_children()[0])  # la plus récente
    attendre(fenetre, 100)
    historique._recharger_selection()
    assert fenetre._page_active == "prediction"
    assert page._champs["Age"].texte() == "41"
    assert page._champs["OverTime"].texte() == "Non"
