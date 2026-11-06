"""Paramètres du modèle : chemins, colonnes retenues et libellés en français.

Tous les chemins sont construits avec le module os à partir du dossier backend/,
ce qui permet de lancer le programme depuis n'importe quel dossier.
"""

import os

DOSSIER_BACKEND = os.path.dirname(os.path.abspath(__file__))
DOSSIER_DONNEES = os.path.join(DOSSIER_BACKEND, "donnees")
DOSSIER_SAUVEGARDE = os.path.join(DOSSIER_BACKEND, "sauvegarde")
DOSSIER_FIGURES = os.path.join(DOSSIER_BACKEND, "figures")

CHEMIN_CSV = os.path.join(DOSSIER_DONNEES, "WA_Fn-UseC_-HR-Employee-Attrition.csv")
NOM_MODELE = "modele_depart.joblib"
NOM_METADONNEES = "metadonnees.json"
NOM_JEU_TEST = "jeu_test.csv"
NOM_REFERENCE = "employes_reference.csv"

GRAINE = 42
PROPORTION_TEST = 0.25
NB_PLIS_VALIDATION = 5
NB_TIRAGES_COURBE = 30
TAILLE_REFERENCE = 40
SEUIL_DECISION = 0.5

COLONNE_CIBLE = "Attrition"
VALEUR_DEPART = "Yes"

# Colonnes retirées au nettoyage, avec la raison (reprise dans DECISIONS.md).
COLONNES_RETIREES = {
    "EmployeeCount": "constante (toujours 1)",
    "StandardHours": "constante (toujours 80)",
    "Over18": "constante (toujours « Y »)",
    "EmployeeNumber": "identifiant d'employé, sans valeur prédictive",
    "DailyRate": "sans lien avec le salaire mensuel (r = 0,01) : bruit",
    "HourlyRate": "sans lien avec le salaire mensuel (r = -0,02) : bruit",
    "MonthlyRate": "sans lien avec le salaire mensuel (r = 0,03) : bruit",
    "Gender": "motif de discrimination interdit, apport négligeable au modèle",
}

GROUPES = [
    "Profil personnel",
    "Poste",
    "Rémunération",
    "Parcours dans l'entreprise",
    "Satisfaction et équilibre",
]

SATISFACTION = {1: "Faible", 2: "Moyenne", 3: "Élevée", 4: "Très élevée"}

# Description de chaque caractéristique conservée : libellé affiché, type de saisie,
# groupe dans le formulaire et, au besoin, traduction des valeurs du jeu de données.
DESCRIPTIONS = {
    "Age": {"libelle": "Âge (ans)", "type": "numerique", "groupe": "Profil personnel"},
    "MaritalStatus": {
        "libelle": "État civil", "type": "categorielle", "groupe": "Profil personnel",
        "valeurs": {"Single": "Célibataire", "Married": "Marié(e)", "Divorced": "Divorcé(e)"},
    },
    "DistanceFromHome": {
        "libelle": "Distance domicile-travail", "type": "numerique", "groupe": "Profil personnel",
    },
    "Education": {
        "libelle": "Niveau d'études", "type": "ordinale", "groupe": "Profil personnel",
        "valeurs": {1: "Sans études collégiales", 2: "Collégial", 3: "Baccalauréat",
                    4: "Maîtrise", 5: "Doctorat"},
    },
    "EducationField": {
        "libelle": "Domaine d'études", "type": "categorielle", "groupe": "Profil personnel",
        "valeurs": {"Life Sciences": "Sciences de la vie", "Medical": "Médecine",
                    "Marketing": "Marketing", "Technical Degree": "Diplôme technique",
                    "Human Resources": "Ressources humaines", "Other": "Autre"},
    },
    "NumCompaniesWorked": {
        "libelle": "Nombre d'entreprises précédentes", "type": "numerique",
        "groupe": "Profil personnel",
    },
    "TotalWorkingYears": {
        "libelle": "Années d'expérience au total", "type": "numerique",
        "groupe": "Profil personnel",
    },
    "Department": {
        "libelle": "Département", "type": "categorielle", "groupe": "Poste",
        "valeurs": {"Sales": "Ventes", "Research & Development": "Recherche et développement",
                    "Human Resources": "Ressources humaines"},
    },
    "JobRole": {
        "libelle": "Poste occupé", "type": "categorielle", "groupe": "Poste",
        "valeurs": {"Sales Executive": "Cadre des ventes",
                    "Research Scientist": "Chercheur scientifique",
                    "Laboratory Technician": "Technicien de laboratoire",
                    "Manufacturing Director": "Directeur de production",
                    "Healthcare Representative": "Représentant santé",
                    "Manager": "Gestionnaire",
                    "Sales Representative": "Représentant des ventes",
                    "Research Director": "Directeur de recherche",
                    "Human Resources": "Ressources humaines"},
    },
    "JobLevel": {
        "libelle": "Niveau hiérarchique (1 à 5)", "type": "ordinale",
        "groupe": "Poste", "valeurs": {},
    },
    "BusinessTravel": {
        "libelle": "Déplacements professionnels", "type": "categorielle", "groupe": "Poste",
        "valeurs": {"Non-Travel": "Aucun", "Travel_Rarely": "Rares",
                    "Travel_Frequently": "Fréquents"},
    },
    "OverTime": {
        "libelle": "Heures supplémentaires", "type": "categorielle", "groupe": "Poste",
        "valeurs": {"Yes": "Oui", "No": "Non"},
    },
    "MonthlyIncome": {
        "libelle": "Salaire mensuel ($)", "type": "numerique", "groupe": "Rémunération",
    },
    "PercentSalaryHike": {
        "libelle": "Dernière augmentation de salaire (%)", "type": "numerique",
        "groupe": "Rémunération",
    },
    "StockOptionLevel": {
        "libelle": "Options d'achat d'actions", "type": "ordinale", "groupe": "Rémunération",
        "valeurs": {0: "Aucune", 1: "Faibles", 2: "Moyennes", 3: "Élevées"},
    },
    "YearsAtCompany": {
        "libelle": "Années dans l'entreprise", "type": "numerique",
        "groupe": "Parcours dans l'entreprise",
    },
    "YearsInCurrentRole": {
        "libelle": "Années dans le poste actuel", "type": "numerique",
        "groupe": "Parcours dans l'entreprise",
    },
    "YearsSinceLastPromotion": {
        "libelle": "Années depuis la dernière promotion", "type": "numerique",
        "groupe": "Parcours dans l'entreprise",
    },
    "YearsWithCurrManager": {
        "libelle": "Années avec le gestionnaire actuel", "type": "numerique",
        "groupe": "Parcours dans l'entreprise",
    },
    "TrainingTimesLastYear": {
        "libelle": "Formations suivies l'an dernier", "type": "numerique",
        "groupe": "Parcours dans l'entreprise",
    },
    "PerformanceRating": {
        "libelle": "Évaluation du rendement", "type": "ordinale",
        "groupe": "Parcours dans l'entreprise",
        "valeurs": {1: "Faible", 2: "Bonne", 3: "Excellente", 4: "Exceptionnelle"},
    },
    "JobSatisfaction": {
        "libelle": "Satisfaction envers le travail", "type": "ordinale",
        "groupe": "Satisfaction et équilibre", "valeurs": SATISFACTION,
    },
    "EnvironmentSatisfaction": {
        "libelle": "Satisfaction envers l'environnement", "type": "ordinale",
        "groupe": "Satisfaction et équilibre", "valeurs": SATISFACTION,
    },
    "RelationshipSatisfaction": {
        "libelle": "Satisfaction envers les relations", "type": "ordinale",
        "groupe": "Satisfaction et équilibre", "valeurs": SATISFACTION,
    },
    "WorkLifeBalance": {
        "libelle": "Équilibre travail-vie personnelle", "type": "ordinale",
        "groupe": "Satisfaction et équilibre",
        "valeurs": {1: "Mauvais", 2: "Correct", 3: "Bon", 4: "Excellent"},
    },
    "JobInvolvement": {
        "libelle": "Implication dans le travail", "type": "ordinale",
        "groupe": "Satisfaction et équilibre", "valeurs": SATISFACTION,
    },
}

# Explication en langage courant des champs dont le libellé seul peut prêter à confusion
# (affichée dans une bulle d'aide à côté du libellé).
EXPLICATIONS = {
    "DistanceFromHome": "Distance entre le domicile et le lieu de travail, de 1 à 29. Le jeu de données "
                        "d'IBM ne précise pas l'unité (kilomètres ou milles).",
    "Education": "Plus haut diplôme obtenu.",
    "NumCompaniesWorked": "Nombre d'employeurs avant l'entreprise actuelle (0 = premier emploi).",
    "TotalWorkingYears": "Toutes les années de travail, dans cette entreprise et ailleurs.",
    "JobLevel": "Échelon du poste dans l'entreprise : 1 = débutant, 5 = haute direction.",
    "OverTime": "L'employé fait-il régulièrement des heures supplémentaires ? C'est l'information "
                "la plus utile au modèle.",
    "MonthlyIncome": "Salaire brut par mois, en dollars (données fictives d'IBM).",
    "PercentSalaryHike": "Hausse de salaire reçue lors de la dernière révision, en pourcentage.",
    "StockOptionLevel": "Droit d'acheter des actions de l'entreprise à prix avantageux, "
                        "de 0 (aucun) à 3 (élevé).",
    "YearsWithCurrManager": "Depuis combien d'années l'employé travaille sous le même gestionnaire.",
    "TrainingTimesLastYear": "Nombre de formations suivies au cours des 12 derniers mois.",
    "PerformanceRating": "Note de la dernière évaluation annuelle. Dans ce jeu de données, tous les "
                         "employés ont « Excellente » ou « Exceptionnelle ».",
    "EnvironmentSatisfaction": "Satisfaction envers le milieu de travail : locaux, ambiance, outils.",
    "RelationshipSatisfaction": "Satisfaction envers les relations avec les collègues et le gestionnaire.",
    "JobInvolvement": "À quel point l'employé s'investit dans son travail, selon l'entreprise.",
    "WorkLifeBalance": "Équilibre entre le travail et la vie personnelle, déclaré par l'employé.",
}

# Règles de cohérence entre deux champs : il faut petit + écart <= grand.
# Elles sont vraies pour les 1470 employés du jeu de données.
REGLES_COHERENCE = [
    ("YearsInCurrentRole", "YearsAtCompany", 0,
     "les années dans le poste actuel ne peuvent pas dépasser les années dans l'entreprise"),
    ("YearsSinceLastPromotion", "YearsAtCompany", 0,
     "les années depuis la dernière promotion ne peuvent pas dépasser les années dans l'entreprise"),
    ("YearsWithCurrManager", "YearsAtCompany", 0,
     "les années avec le gestionnaire ne peuvent pas dépasser les années dans l'entreprise"),
    ("YearsAtCompany", "TotalWorkingYears", 0,
     "les années dans l'entreprise ne peuvent pas dépasser l'expérience totale"),
    ("TotalWorkingYears", "Age", 14,
     "l'expérience totale ne peut pas dépasser l'âge moins 14 ans"),
]
