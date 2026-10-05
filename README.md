# EduPaie 💰

Application desktop de **gestion des paiements scolaires** : élèves, encaissements,
reçus numérotés et PDF, tableau de bord. Développée en **Python + PySide6** avec une
architecture en couches stricte, livrée avec un **exécutable Windows** autonome.

```
ui  →  services  →  data  →  domain
```

Chaque couche n'importe que celle d'en dessous : aucune règle métier dans l'UI,
aucun SQL hors de `data/`, aucun Qt ni SQL dans le `domain/`.

## Fonctionnalités

- **Élèves** : fiche complète (nom, prénom, classe, **année scolaire**, frais dus),
  recherche instantanée, filtres par classe et par statut.
- **Paiements** : espèces, mobile money, virement, chèque — montants **entiers en FCFA**
  (zéro erreur d'arrondi) ; le solde ne passe **jamais** sous 0 : tout surpaiement est refusé.
- **Reçus** : numérotation `REC-AAAA-000042` sans doublon, **instantané figé** —
  une réimpression est strictement identique, même si l'élève change ensuite.
- **Tableau de bord** : encaissé, reste à recouvrer, taux de recouvrement,
  répartition par statut, synthèse par classe, derniers paiements.
- **PDF** : reçu A5 généré avec fpdf2, ouvert directement depuis la fiche élève.
- **Robustesse** : une seule transaction par paiement (tout-ou-rien),
  erreurs affichées dans des boîtes dialogue (plus aucun crash silencieux),
  journal rotatif dans `%APPDATA%\EduPaie\logs\`.

## Installation (développement)

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

## Lancement

| Action | Commande |
|---|---|
| Lancer l'app (dev) | `set EDUPAIE_DEBUG=1 && python main.py` |
| Tests | `pytest -q` |
| Lint | `ruff check .` |
| Régénérer la base de test | `python scripts/seed_db.py` |
| Régénérer l'icône | `python scripts/generate_icon.py` |
| Build de l'exe | `build.bat` (ou `python scripts/build_exe.py`) |

Au premier démarrage, la base `resources/seed/edupaie_seed.db` (jeu de test, livrable)
est copiée vers `%APPDATA%\EduPaie\edupaie.db` (ou `edupaie_dev.db` avec
`EDUPAIE_DEBUG=1`) : les données survivent aux mises à jour de l'exécutable.

## Structure

```
main.py                  Point d'entrée (appelle app.run())
src/edupaie/
├── app.py               Composition root : DB → migrations → repos → services → UI
├── config.py            Chemins AppData + resource_path() dev/PyInstaller
├── domain/              Modèles, enums, exceptions — aucune dépendance
├── data/                sqlite3, migrations versionnées, repositories (tout le SQL)
├── services/            Règles métier : solde, statuts, validation, transaction
├── reports/             Génération PDF des reçus (fpdf2)
├── ui/                  PySide6 : fenêtre, vues, dialogues, modèles Qt, thème
└── utils/               Formatage FR, journalisation
resources/               Icônes + base de jeu de test (embarquées dans l'exe)
tests/                   pytest, sans Qt (48 tests)
docs/                    Architecture, MCD/MLD, guide utilisateur
scripts/                 seed_db, generate_icon, build_exe
```

## Architecture

Voir [docs/architecture.md](docs/architecture.md) (schéma des couches et flux d'un
paiement) et [docs/mcd_mld.svg](docs/mcd_mld.svg) (modèle de données).

Points clés du sujet :

1. **Argent en entier** — tous les montants sont des `int` en FCFA.
2. **Reçu = snapshot figé** — nom, classe, montant, solde après paiement copiés
   dans `receipts` au moment de l'émission.
3. **Numérotation sans doublon** — table `receipt_counter` incrémentée **dans la
   même transaction** que le paiement ; rollback ⇒ numéro jamais consommé.
4. **Une transaction par paiement** — valider → vérifier le solde → insérer le
   paiement → créer le reçu → commit.
5. **Base dans AppData** — indispensable avec `--onefile` (dossier temporaire).
6. **Injection de dépendances** — les services reçoivent leurs repositories,
   `app.py` assemble le tout, les tests utilisent une base isolée sans Qt.
7. **Modèles Qt dédiés** — `QAbstractTableModel` + `QSortFilterProxyModel`
   pour un tri et un filtrage propres.

## Build Windows

```bat
build.bat
```

Produit `dist\EduPaie.exe` (one-file, fenêtré, icône embarquée). À tester sur une
machine propre ; un blocage antivirus est un faux positif classique du mode one-file.

## Guide utilisateur

Voir [docs/user_guide.md](docs/user_guide.md).
