-- Schéma initial EduPaie.
-- Montants entiers en FCFA (jamais de REAL). Dates en ISO AAAA-MM-JJ (TEXT).

CREATE TABLE students (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name     TEXT    NOT NULL,
    last_name      TEXT    NOT NULL,
    class_name     TEXT    NOT NULL,
    school_year    TEXT    NOT NULL DEFAULT '',   -- ex. 2026-2027
    guardian_phone TEXT    NOT NULL DEFAULT '',
    email          TEXT    NOT NULL DEFAULT '',
    annual_fee     INTEGER NOT NULL DEFAULT 0 CHECK (annual_fee >= 0),
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);

CREATE INDEX idx_students_class ON students (class_name);
CREATE INDEX idx_students_name  ON students (last_name, first_name);

CREATE TABLE payments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    amount     INTEGER NOT NULL CHECK (amount > 0),
    mode       TEXT    NOT NULL CHECK (mode IN ('ESPECES', 'MOBILE_MONEY', 'VIREMENT', 'CHEQUE')),
    paid_on    TEXT    NOT NULL,
    note       TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL
);

CREATE INDEX idx_payments_student ON payments (student_id);
CREATE INDEX idx_payments_paid_on ON payments (paid_on);

-- Reçu = snapshot figé : copie des données au moment de l'émission.
CREATE TABLE receipts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    number           TEXT    NOT NULL UNIQUE,          -- REC-2026-000042
    payment_id       INTEGER NOT NULL UNIQUE REFERENCES payments (id) ON DELETE CASCADE,
    student_id       INTEGER NOT NULL REFERENCES students (id) ON DELETE CASCADE,
    student_name     TEXT    NOT NULL,
    class_name       TEXT    NOT NULL,
    amount           INTEGER NOT NULL,
    mode             TEXT    NOT NULL,
    paid_on          TEXT    NOT NULL,
    balance_after    INTEGER NOT NULL,
    total_paid_after INTEGER NOT NULL,
    issued_at        TEXT    NOT NULL
);

CREATE INDEX idx_receipts_student ON receipts (student_id);

-- Compteur de numérotation, incrémenté dans la même transaction que le paiement.
CREATE TABLE receipt_counter (
    year  INTEGER PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);
