# Architecture EduPaie

## Règle de dépendance : `ui → services → data → domain`

Une seule flèche compte : **chaque couche n'importe que celle d'en dessous**.

```
┌─────────────────────────────────────────────────────────────────┐
│  ui/          PySide6 : fenêtres, vues, dialogues, modèles Qt   │  zéro SQL,
│               + reports/ (PDF depuis un Receipt)                │  zéro règle
├─────────────────────────────────────────────────────────────────┤
│  services/    Règles métier : solde = dû − Σ paiements,         │  zéro SQL,
│               statuts dérivés, validations, transactions        │  zéro Qt
├─────────────────────────────────────────────────────────────────┤
│  data/        sqlite3, migrations versionnées (user_version),   │  zéro règle
│               repositories : tout le SQL est ici                │  métier
├─────────────────────────────────────────────────────────────────┤
│  domain/      dataclasses, enums, exceptions                    │  aucune
│               Aucune dépendance (ni SQL, ni Qt)                 │  dépendance
└─────────────────────────────────────────────────────────────────┘
```

Imports interdits (verrouillés par convention, vérifiables à la main) :

- `domain/` n'importe **rien** du projet (uniquement la bibliothèque standard) ;
- `data/` n'importe ni `services`, ni `ui`, ni Qt ;
- `services/` n'importe ni `ui`, ni PySide6, ni n'écrit de SQL brut ;
- `ui/` n'écrit jamais de SQL et ne contient aucune règle de calcul :
  elle appelle les services et affiche leurs résultats.

`utils/` (formatage, journal) et `config.py` sont des feuilles : utilisables par
toutes les couches, ils n'importent aucune couche applicative.

## Composition root

`app.py` assemble tout, dans l'ordre :

```
ensure_database()          copie du seed vers %APPDATA%/EduPaie/ au 1er lancement
       │
Database(config.DB_PATH)   connexion sqlite3 (foreign_keys ON, WAL, transactions)
       │
Migrator(...).migrate()    applique data/migrations/001_*.sql (PRAGMA user_version)
       │
Repositories               StudentRepository, PaymentRepository, ReceiptRepository
       │
Services                    StudentService, PaymentService, ReceiptService,
       │                    DashboardService — chacun reçoit ses repositories
       │
MainWindow                 construit les vues avec leurs services (injection)
```

Les tests font exactement la même assemblage dans `tests/conftest.py`, sans Qt :
une base fichier isolée par test + les mêmes services.

## Flux d'un paiement (la transaction du sujet)

```
PaymentDialog (ui)
   │  montant, mode, date, note
   ▼
PaymentService.register()
   │  1. validators : montant entier > 0, mode valide, date valide
   │  2. BEGIN IMMEDIATE ────────────────┐  transaction
   │  3. lire l'élève (NotFound si absent)│
   │  4. solde = annual_fee − Σ paiements │
   │     si montant > solde : ROLLBACK ◄──┘ → OverpaymentError
   │        (le solde est jamais < 0, aucun numéro consommé)
   │  5. INSERT payments
   │  6. receipt_counter += 1  →  REC-2026-000042
   │  7. INSERT receipts (snapshot figé)
   │  COMMIT ────────────────────────────┘  sinon ROLLBACK complet
   ▼
(retourne Payment, Receipt) → la vue rafraîchit et peut ouvrir le PDF
```

Toute erreur en 1-7 annule **tout** : ni paiement fantôme, ni numéro sauté.

## Pourquoi un snapshot dans `receipts` ?

Le reçu recopie `student_name`, `class_name`, `amount`, `paid_on`,
`total_paid_after`, `balance_after` au moment de l'émission. Le PDF est ensuite
généré **uniquement à partir de cette ligne** (reports/receipt_pdf.py), avec une
date de création figée : deux réimpressions produisent des octets identiques
(testé dans `tests/test_receipt_pdf.py`), même si l'élève est renommé ou son
tarif modifié entre-temps.

## Emplacement des données (PyInstaller `--onefile`)

À chaque lancement, l'exe se décompresse dans un dossier temporaire : écrire la
base à côté serait perdu. `config.resource_path()` sert pour les **ressources en
lecture** (icônes, seed, migrations, thème) et `config.data_dir()` pour les
**écritures** (base, logs, reçus) dans `%APPDATA%\EduPaie\`.

## Décisions structurantes

| Décision | Pourquoi |
|---|---|
| Montants en `int` (FCFA) | Aucune erreur d'arrondi sur les soldes |
| Statut dérivé, jamais stocké | Impossible à désynchroniser du solde |
| `QAbstractTableModel` + proxy | Tri/filtrage performants, code lisible |
| Repositories sans transaction interne | Le service découpe sa propre transaction multi-repos |
| Erreurs métier = exceptions `domain/` | La UI décide du message, la règle reste testable sans Qt |
| `sys.excepthook` → `QMessageBox` | Toute erreur non catchée est journalisée + affichée |
