# Risque de départ d'un employé — INF1007, projet 2

Maxime Hamrioui et Alexandre Bertrand-Beaudet · automne 2026

Application de bureau à thème sombre (CustomTkinter) qui estime le **risque qu'un employé quitte
son entreprise** à partir de 26 caractéristiques de sa vie professionnelle et personnelle (âge, état
civil, poste, salaire, heures supplémentaires, ancienneté, satisfaction, équilibre travail-vie
personnelle…).

Le formulaire accepte des **saisies partielles** : chaque champ vide fait baisser la **précision
attendue**, affichée en direct avec un graphique « précision selon le nombre de champs remplis ».

> ⚠ **Exercice pédagogique.** Les données sont fictives et le modèle se trompe environ une fois
> sur quatre. Plusieurs variables (âge, état civil) sont des motifs de discrimination interdits :
> l'outil ne doit jamais servir à une décision réelle concernant un employé.

## Installation et lancement

Python 3.11 ou plus récent, depuis le dossier du dépôt :

```bash
python -m pip install -r requirements.txt
python main.py               # ouvre l'interface graphique
python main.py entrainer     # (re)entraîne le modèle, environ 25 s
python -m pytest             # lance les 122 tests
python -m coverage run -m pytest && python -m coverage report   # couverture
```

Le modèle entraîné est fourni dans `backend/sauvegarde/` : l'interface ne réentraîne rien au
lancement. Si ces fichiers manquent ou ont été créés avec une autre version de scikit-learn,
l'interface propose de relancer l'entraînement.

**Dépannage.** Les bibliothèques doivent être installées pour le Python qui lance `main.py`. Dans
VS Code, c'est l'interpréteur affiché en bas à droite (Ctrl+Maj+P → « Python: Select
Interpreter »). S'il manque une bibliothèque, `main.py` affiche le Python utilisé et la commande
exacte à exécuter.

## Organisation du dépôt

Le code tient dans deux dossiers : `backend/` (données, apprentissage, graphiques du modèle) et
`frontend/` (l'application et sa fenêtre), avec les fichiers Python directement dedans.
`frontend/` utilise `backend/`, jamais l'inverse.

```
backend/
├── config.py            chemins (module os), colonnes retenues, libellés français, règles de cohérence
├── exceptions.py        ErreurProjet → DonneeInvalideError → SaisieInvalideError, FichierIntrouvableError, ...
├── variables.py         Variable (abstraite) → VariableNumerique, VariableCategorielle → VariableOrdinale
├── jeu_de_donnees.py    JeuDeDonnees : lecture par blocs, nettoyage, séparation ; lecture/écriture JSON et CSV
├── modeles.py           Modele (abstraite) → ModeleReference, ModeleLogistique, ModeleForetAleatoire
├── metriques.py         métriques NumPy vectorisées (comparées à scikit-learn dans les tests)
├── saisie_partielle.py  prédiction avec champs vides, précision attendue, effet de chaque champ
├── entrainement.py      pipeline complet : exploration, comparaison, sauvegarde
├── style.py             thèmes clair (figures enregistrées) et sombre (interface) des graphiques
├── graphiques.py        graphiques d'exploration et d'évaluation
├── donnees/             jeu de données IBM (CSV)
├── sauvegarde/          modèle (joblib), métadonnées (JSON), jeu de test et employés de référence (CSV)
├── figures/             graphiques enregistrés par l'entraînement
└── tests/               tests du back end (+ fixtures.py, partagé avec frontend/tests)

frontend/
├── application.py       Application (composition : modèle + variables + historique) et Prediction
├── historique.py        Historique : ajout et lecture du CSV des prédictions
├── fenetre.py           FenetrePrincipale : barre latérale de navigation, avertissement
├── pages.py             PagePrediction, PageModele, PageHistorique, PageAPropos
├── composants.py        Carte, Tuile, Champ, ZoneGraphique, boutons
├── theme.py             palette sombre et polices
├── graphiques.py        graphiques de l'interface (précision, facteurs, position)
└── tests/               tests de la logique de l'application

main.py                  point d'entrée (argparse)
```

`application.py` et `historique.py` ne dépendent d'aucune fenêtre : ils sont testés. Les fichiers
d'affichage (`fenetre.py`, `pages.py`, `composants.py`) n'effectuent aucun calcul : ils appellent
`Application`. À la racine se trouvent aussi les fichiers exigés par l'énoncé (`README.md`,
`requirements.txt`, avec `DECISIONS.md`, `JOURNAL_IA.md` et l'énoncé dans `docs/`), la configuration des tests (`pyproject.toml`)
et la CI (`.github/workflows/`, emplacement imposé par GitHub).

## Utilisation

La barre latérale donne accès à quatre pages ; l'avertissement y reste toujours visible.

1. **Prédiction** : remplissez autant de champs que vous voulez (ou chargez un des « exemples
   réels » tirés du jeu de test), puis cliquez sur **Prédire** (ou appuyez sur Entrée).
   - En haut à droite : le risque de départ (pourcentage, badge coloré, barre) et la **précision
     attendue** avec le nombre de champs remplis et les champs les plus utiles à remplir ensuite.
   - Trois graphiques : précision selon le nombre de champs (avec votre position), facteurs qui
     influencent le résultat, position de l'employé parmi ceux du jeu de test.
   - Une saisie invalide est signalée sous le champ, en rouge, dès qu'on le quitte ; à la
     prédiction, toutes les erreurs (y compris les incohérences entre deux champs) sont affichées
     d'un coup. Aucune erreur ne fait planter l'application.
2. **Le modèle** : indicateurs clés, comparaison avec la référence, matrice de confusion, variables
   les plus utiles, comparaison « satisfaction ou départ ».
3. **Historique** : chaque prédiction est ajoutée à `frontend/historique_predictions.csv` ;
   cliquez sur une ligne pour revoir ses saisies.
4. **À propos** : lecture des résultats, limites, source des données.

## Jeu de données

| | |
|---|---|
| Nom | IBM HR Analytics Employee Attrition & Performance |
| Source | Kaggle, <https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset> |
| Licence | Open Database License (base de données) et Database Contents License (contenu) : redistribution permise avec attribution |
| Taille | 1470 lignes, 35 colonnes (dont 26 caractéristiques conservées : 11 numériques, 8 échelles ordonnées, 7 catégorielles) |
| Données personnelles | Aucune : employés fictifs créés par des scientifiques des données d'IBM |
| Fichier | `backend/donnees/WA_Fn-UseC_-HR-Employee-Attrition.csv` (228 Ko) |

**Cible :** `Attrition` (l'employé a-t-il quitté l'entreprise ? 16 % de « oui »), donc une
**classification binaire**. Nous voulions d'abord prédire la satisfaction au travail, mais elle n'est
pas prévisible avec ces données (voir [DECISIONS.md](docs/DECISIONS.md)).

## Résultats du modèle

Séparation stratifiée 75 % / 25 % (graine 42) : 1102 employés d'entraînement, 368 de test (59 départs).
**Métrique principale : l'exactitude équilibrée** (moyenne des taux de bonnes réponses chez les
partis et chez les restés), car l'exactitude simple est trompeuse : répondre toujours « reste »
donne déjà 84 %.

| Modèle | Exactitude équilibrée (test) | Validation croisée (5 plis, entraînement) | Exactitude | Rappel des départs | AUC |
|---|---|---|---|---|---|
| Référence (classe majoritaire) | 50,0 % | 50,0 % | 84,0 % | 0 % | 0,50 |
| **Régression logistique (retenue)** | **72,5 %** | **75,6 %** | 79,1 % | 62,7 % | 0,81 |
| Forêt aléatoire | 73,5 % | 73,8 % | 83,2 % | 59,3 % | 0,78 |

Le modèle est choisi par validation croisée sur l'entraînement (le test ne sert qu'à mesurer). La
forêt fait un peu mieux sur le test (+1 point), mais moins bien en validation croisée et en AUC :
avec 59 départs seulement, cet écart est dans l'incertitude (environ ± 3 points).

**Précision selon les champs remplis** (exactitude équilibrée sur le test) :

| Champs remplis | 0 | 1 | 2 | 5 | 10 | 26 |
|---|---|---|---|---|---|---|
| Les plus utiles d'abord | 50 % | 69 % | 71 % | 68 % | 70 % | 72,5 % |
| Au hasard (moyenne de 30 tirages) | 50 % | 51 % | 53 % | 58 % | 62 % | 72,5 % |

Les heures supplémentaires suffisent presque à elles seules : savoir qu'un employé en fait donne
déjà 69 %. **Limites :** données fictives ; modèle linéaire ; peu de départs dans le test ; le
« risque » n'est pas une probabilité calibrée (les classes sont pondérées à l'entraînement).

**Satisfaction au lieu du départ :** la régression logistique obtient 44 % d'exactitude équilibrée
pour prédire « satisfait (3 ou 4 sur 4) », moins bien que la référence (50 %).

Graphiques produits par l'entraînement, dans `backend/figures/` : `exploration_taux_depart.png`,
`exploration_satisfaction.png`, `comparaison_cibles.png`, `matrice_confusion.png`, `importances.png`.

## Comment fonctionne la précision attendue

Quand un champ est vide, on ne connaît pas sa valeur. Le modèle essaie alors les valeurs de **40
vrais employés de référence** (tirés de l'entraînement) et fait la moyenne des 40 risques
([backend/saisie_partielle.py](backend/saisie_partielle.py), calcul vectorisé
avec `np.repeat` / `np.tile`, sans boucle). Le même calcul, appliqué aux 368 employés de test en ne
gardant que les champs remplis, donne la précision attendue. Elle est mise en cache pour chaque
combinaison de champs.

Une première version remplaçait chaque champ vide par la médiane : avec un ou deux champs remplis,
l'employé « médian » restait toujours sous le seuil de 50 % et la précision restait bloquée à 50 %.
La moyenne sur des employés réels fait passer la précision avec le seul champ « heures
supplémentaires » de 50 % à 69 %.

## Programmation orientée objet

2 hiérarchies avec classe parente abstraite et polymorphisme (`Variable.valider` / `formater`,
`Modele._creer_estimateur`), plus la hiérarchie des exceptions ; composition (`Application`
contient le `Modele`, les `Variable` et l'`Historique` ; `FenetrePrincipale` contient les pages,
qui contiennent l'`Application` et les `Champ`) ; attributs protégés exposés par des propriétés ;
méthodes spéciales `__str__`, `__repr__`, `__eq__`, `__hash__`, `__len__`.

### Outils du chapitre 7

- **Décorateur** `chronometre` ([backend/modeles.py](backend/modeles.py)) :
  mesure la durée de `Modele.entrainer` et la range dans l'objet, sans mélanger le chronométrage au
  code d'entraînement.
- **Générateur** `lire_par_blocs` ([backend/jeu_de_donnees.py](backend/jeu_de_donnees.py)) :
  produit le CSV 500 lignes à la fois avec `yield from`, ce qui permettrait de lire un fichier trop
  gros pour la mémoire.
- **Lambda** comme clé de tri : trier les variables par importance, l'historique par date, choisir
  le modèle de meilleure validation croisée (`max(..., key=lambda modele: ...)`).

## Tests et couverture

122 tests pytest, dans `backend/tests/` et `frontend/tests/` : cas usuels, cas limites (bornes
incluses, formulaire vide, une seule classe) et cas d'erreur (`pytest.raises`), avec `pytest.approx`
pour les flottants. Les métriques NumPy et le calcul vectorisé des champs vides sont vérifiés contre
scikit-learn et contre une boucle écrite à la main. GitHub Actions lance les tests à chaque `push`
([.github/workflows/tests.yml](.github/workflows/tests.yml)).

**Couverture (coverage 7.17) : 97 %** des instructions de `backend/` et `frontend/`, hors fenêtres
CustomTkinter (`fenetre.py`, `pages.py`, `composants.py`, `theme.py`), vérifiées à la main pendant la démo
(voir `pyproject.toml`).

## Documentation consultée

- pandas — `read_csv` (paramètre `chunksize`) : <https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html>
- scikit-learn — `LogisticRegression` (paramètre `class_weight`) : <https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html>
- scikit-learn — `ColumnTransformer` : <https://scikit-learn.org/stable/modules/compose.html#columntransformer-for-heterogeneous-data>
- scikit-learn — exactitude équilibrée : <https://scikit-learn.org/stable/modules/model_evaluation.html#balanced-accuracy-score>
- scikit-learn — importance par permutation : <https://scikit-learn.org/stable/modules/permutation_importance.html>
- scikit-learn — sauvegarde des modèles : <https://scikit-learn.org/stable/model_persistence.html>
- CustomTkinter : <https://customtkinter.tomschimansky.com/documentation/>
- Tkinter / ttk (tableaux `Treeview`) : <https://docs.python.org/3/library/tkinter.ttk.html>
- Matplotlib dans Tkinter : <https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_tk_sgskip.html>
- pytest, exceptions attendues : <https://docs.pytest.org/en/stable/how-to/assert.html>
- GitHub Actions pour Python : <https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python>

Choix et justifications : [DECISIONS.md](docs/DECISIONS.md) · usage de l'IA : [JOURNAL_IA.md](docs/JOURNAL_IA.md)
