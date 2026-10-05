-- Numéro de caissier et note de paiement sur le reçu (snapshot figé).
-- Ajout en colonne : les anciennes lignes conservent '' par défaut.

ALTER TABLE receipts ADD COLUMN caissier TEXT NOT NULL DEFAULT '';
ALTER TABLE receipts ADD COLUMN note TEXT    NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_receipts_number ON receipts (number);
