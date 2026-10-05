"""Repository paiements."""

from edupaie.data.database import Database
from edupaie.domain.enums import PaymentMode
from edupaie.domain.models import Payment


def row_to_payment(row) -> Payment:
    return Payment(
        id=row["id"],
        student_id=row["student_id"],
        amount=row["amount"],
        mode=PaymentMode(row["mode"]),
        paid_on=row["paid_on"],
        note=row["note"],
        created_at=row["created_at"],
    )


PAYMENT_COLUMNS = "id, student_id, amount, mode, paid_on, note, created_at"


class PaymentRepository:
    def __init__(self, db: Database):
        self.db = db

    # --- écritures -----------------------------------------------------

    def insert(self, conn, payment: Payment) -> int:
        """Insère dans la transaction fournie. Retourne l'id."""
        cur = conn.execute(
            "INSERT INTO payments (student_id, amount, mode, paid_on, note, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                payment.student_id,
                payment.amount,
                payment.mode.value,
                payment.paid_on,
                payment.note,
                payment.created_at,
            ),
        )
        return cur.lastrowid

    def delete(self, payment_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

    # --- lectures ------------------------------------------------------

    def get(self, payment_id: int) -> Payment | None:
        with self.db.connection() as conn:
            row = conn.execute(
                f"SELECT {PAYMENT_COLUMNS} FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
        return row_to_payment(row) if row else None

    def list_for_student(self, student_id: int) -> list[Payment]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {PAYMENT_COLUMNS} FROM payments WHERE student_id = ?"
                " ORDER BY paid_on DESC, id DESC",
                (student_id,),
            ).fetchall()
        return [row_to_payment(row) for row in rows]

    def total_for_student(self, student_id: int, conn=None) -> int:
        """Somme des paiements d'un élève (transaction externe possible)."""
        if conn is not None:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE student_id = ?",
                (student_id,),
            ).fetchone()
            return row[0]
        with self.db.connection() as own:
            row = own.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE student_id = ?",
                (student_id,),
            ).fetchone()
        return row[0]

    def sum_between(self, start_iso: str, end_iso: str) -> int:
        """Total encaissé entre deux dates (bornes incluses)."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE paid_on BETWEEN ? AND ?",
                (start_iso, end_iso),
            ).fetchone()
        return row[0]

    def recent(self, limit: int = 10) -> list[Payment]:
        with self.db.connection() as conn:
            rows = conn.execute(
                f"SELECT {PAYMENT_COLUMNS} FROM payments ORDER BY paid_on DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [row_to_payment(row) for row in rows]

    def count(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
