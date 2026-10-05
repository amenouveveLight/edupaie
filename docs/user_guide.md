# Guide utilisateur — EduPaie

## 1. Première ouverture

1. Double-cliquez sur **EduPaie.exe** (ou `python main.py` en développement).
2. Au tout premier lancement, l'application crée sa base dans
   `%APPDATA%\EduPaie\edupaie.db` à partir du jeu de test : 12 élèves et
   17 paiements sont déjà saisis pour la démonstration.
3. Vous arrivez sur le **Tableau de bord**.

> En développement (`EDUPAIE_DEBUG=1`), une base séparée `edupaie_dev.db` est
> utilisée : vos essais n'abîment jamais les données de démonstration.

## 2. Le tableau de bord

- **Élèves inscrits / Total encaissé / Reste à recouvrer / Taux de recouvrement** :
  calculés en direct.
- **Répartition** : nombre d'élèves non payés, en partie payés, soldés.
- **Derniers paiements** : cliquez un en-tête de colonne pour trier.
- **Synthèse par classe** : encaissé et reste dû pour chaque classe.

La page se rafraîchit automatiquement à chaque affichage.

## 3. Gérer les élèves

Menu **Élèves** à gauche :

| Action | Comment |
|---|---|
| Rechercher | Tapez un nom, un prénom ou une classe (filtre instantané) |
| Filtrer | Liste déroulante **classe** et **statut** |
| Trier | Cliquez sur un en-tête de colonne |
| Ouvrir une fiche | **Double-cliquez** sur la ligne |
| Ajouter | Bouton **Ajouter un élève** |
| Modifier / Supprimer | Sélectionnez une ligne, puis le bouton |

⚠️ Le formulaire demande le **prénom, le nom, la classe, l'année scolaire**
(pré-remplie avec l'année en cours, format 2026-2027) et les **frais annuels** ;
le tuteur et l'e-mail sont facultatifs.

⚠️ La suppression est **refusée si l'élève a déjà des paiements** (traçabilité
comptable). Modifiez plutôt sa fiche.

## 4. Encaisser un paiement

1. Ouvrez la fiche de l'élève (bouton **Nouveau paiement** en haut).
2. Saisissez le **montant** (entier, FCFA) : le solde après paiement s'affiche
   en direct sous le champ.
3. Choisissez le **mode** (Espèces, Mobile Money, Virement, Chèque), la
   **date** (aujourd'hui par défaut, jamais dans le futur) et une note facultative.
4. Validez.

Si le montant **dépasse le solde restant**, un avertissement orange apparaît
immédiatement et l'enregistrement est **refusé** : un paiement ne peut jamais
rendre le solde négatif. Réduisez le montant pour continuer.

À l'enregistrement réussi, le reçu `REC-AAAA-000001` est créé **dans la même
transaction** que le paiement, et l'application propose d'ouvrir le PDF.

## 5. Les reçus

- **Réimpression** : dans la fiche élève, double-cliquez une ligne de
  l'historique, ou cliquez **Ouvrir le dernier reçu**.
- Le PDF est régénéré à partir du **snapshot figé** du reçu : il est
  **strictement identique** à chaque réimpression, même si l'élève a changé de
  classe ou de tarif entre-temps.
- Les PDF sont conservés dans `%APPDATA%\EduPaie\receipts\REC-...pdf`.

## 6. Où sont les données ?

| Quoi | Où |
|---|---|
| Base de données | `%APPDATA%\EduPaie\edupaie.db` |
| Journal (diagnostic) | `%APPDATA%\EduPaie\logs\edupaie.log` |
| Reçus PDF | `%APPDATA%\EduPaie\receipts\` |

Pour sauvegarder, copiez simplement `edupaie.db` (arrêt de l'application en
cours). Pour réinitialiser la démonstration : supprimez `edupaie.db` et
relancez, le jeu de test est recopié automatiquement.

## 7. En cas d'erreur

Une boîte rouge explique le problème ; le détail complet est toujours écrit
dans `logs\edupaie.log` (fichier tournant, 500 Ko × 3). L'application reste
ouverte : aucun crash silencieux.
