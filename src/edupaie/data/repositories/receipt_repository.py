"""Repository reçus : snapshot figé + compteur de numérotation."""

from edupaie.data.database import Database
from edupaie.domain.enums import PaymentMode
from edupaie.domain.models import Receipt

RECEIPT_COLUMNS = (
    "id, number, payment_id, student_id, student_name, class_name, amount,"
    " mode, paid_on, balance_after, total_paid_after, issued_at, caissier, note"
)


def row_to_receipt(row) -> Receipt:
    return Receipt(
        id=row["id"],
        number=row["number"],
        payment_id=row["payment_id"],
        student_id=row["student_id"],
        student_name=row["student_name"],
        class_name=row["class_name"],
        amount=row["amount"],
        mode=PaymentMode(row["mode"]),
        paid_on=row["paid_on"],
        balance_after=row["balance_after"],
        total_paid_after=row["total_paid_after"],
        issued_at=row["issued_at"],
        caissier=row["caissier"],
        note=row["note"],
    )


class ReceiptRepository:
    def __init__(self, db: Database):
        self.db = db

    # --- numérotation --------------------------------------------------

    def next_number(self, conn, year: int) -> str:
        """Incrémente le compteur de l'année DANS la transaction fournie.

        Si la transaction échoue plus tard, le rollback remet le compteur
        à l'ordre : aucun numéro n'est jamais consommé deux fois ni sauté.
        """
        row = conn.execute("SELECT value FROM receipt_counter WHERE year = ?", (year,)).fetchone()
        if row is None:
            seq = 1
            conn.execute("INSERT INTO receipt_counter (year, value) VALUES (?, ?)", (year, seq))
        else:
            seq = row["value"] + 1
            conn.execute("UPDATE receipt_counter SET value = ? WHERE year = ?", (seq, year))
        return f"REC-{year}-{seq:06d}"

    # --- écritures -----------------------------------------------------

    def insert(self, conn, receipt: Receipt) -> int:
        cur = conn.execute(
            "INSERT INTO receipts (number, payment_id, student_id, student_name, class_name,"
            " amount, mode, paid_on, balance_after, total_paid_after, issued_at, caissier, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                receipt.number,
                receipt.payment_id,
                receipt.student_id,
                receipt.student_name,
                receipt.class_name,
                receipt.amount,
                receipt.mode.value,
                receipt.paid_on,
                receipt.balance_after,
                receipt.total_paid_after,
                receipt.issued_at,
                receipt.caissier,
                receipt.note,
            ),
        )
        return cur.lastrowid

    # --- lectures ------------------------------------------------------

    def get(self, receipt_id: int) -> Receipt | None:
        with self.db.connection() as conn:
            row = conn.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE id = ?", (receipt_id,)
            ).fetchone()
        return row_to_receipt(row) if row else None

    def get_by_number(self, number: str) -> Receipt | None:
        with self.db.connection() as conn:
            row = conn.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE number = ?", (number,)
            ).fetchone()
        return row_to_receipt(row) if row else None

    def get_by_payment_id(self, payment_id: int) -> Receipt | None:
        with self.db.connection() as conn:
            row = conn.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE payment_id = ?", (payment_id,)
            ).fetchone()
        return row_to_receipt(row) if row else None

    def list_for_student(self, student_id: int) -> list[Receipt]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {RECEIPT_COLUMNS} FROM receipts WHERE student_id = ?"
                " ORDER BY issued_at DESC, id DESC",
                (student_id,),
            ).fetchall()
        return [row_to_receipt(row) for row in rows]

    def count(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
