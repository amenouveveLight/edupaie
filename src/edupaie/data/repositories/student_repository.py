"""Repository élèves : toute la requête SQL relative aux élèves est ici."""

from __future__ import annotations

from edupaie.data.database import Database
from edupaie.domain.models import Student, StudentAccount

COLUMNS = (
    "id, first_name, last_name, class_name, school_year, guardian_phone, email,"
    " annual_fee, created_at, updated_at"
)


def row_to_student(row) -> Student:
    return Student(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        class_name=row["class_name"],
        school_year=row["school_year"],
        guardian_phone=row["guardian_phone"],
        email=row["email"],
        annual_fee=row["annual_fee"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class StudentRepository:
    def __init__(self, db: Database):
        self.db = db

    # --- écritures -----------------------------------------------------

    def add(self, student: Student, conn=None) -> Student:
        """Insère un élève. `conn` fourni => transaction externe en cours."""
        if conn is None:
            with self.db.transaction() as tx:
                return self._add(tx, student)
        return self._add(conn, student)

    def _add(self, conn, student: Student) -> Student:
        cur = conn.execute(
            "INSERT INTO students (first_name, last_name, class_name, school_year,"
            " guardian_phone, email, annual_fee, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                student.first_name,
                student.last_name,
                student.class_name,
                student.school_year,
                student.guardian_phone,
                student.email,
                student.annual_fee,
                student.created_at,
                student.updated_at,
            ),
        )
        return student.with_id(cur.lastrowid)

    def update(self, student: Student, conn=None) -> Student:
        if conn is None:
            with self.db.transaction() as tx:
                return self._update(tx, student)
        return self._update(conn, student)

    def _update(self, conn, student: Student) -> Student:
        conn.execute(
            "UPDATE students SET first_name=?, last_name=?, class_name=?, school_year=?,"
            " guardian_phone=?, email=?, annual_fee=?, updated_at=? WHERE id=?",
            (
                student.first_name,
                student.last_name,
                student.class_name,
                student.school_year,
                student.guardian_phone,
                student.email,
                student.annual_fee,
                student.updated_at,
                student.id,
            ),
        )
        return student

    def delete(self, student_id: int) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))

    # --- lectures ------------------------------------------------------

    def get(self, student_id: int) -> Student | None:
        with self.db.connection() as conn:
            return self.get_conn(conn, student_id)

    def get_conn(self, conn, student_id: int) -> Student | None:
        row = conn.execute(f"SELECT {COLUMNS} FROM students WHERE id = ?", (student_id,)).fetchone()
        return row_to_student(row) if row else None

    def list(self, search: str = "", class_name: str | None = None) -> list[StudentAccount]:
        """Élèves avec total réglé, éventuellement filtrés (recherche, classe).

        Le filtre par statut est appliqué par les services (règle métier),
        pas ici.
        """
        clauses, params = [], []
        if search.strip():
            like = f"%{search.strip().lower()}%"
            clauses.append(
                "(lower(s.first_name || ' ' || s.last_name) LIKE ?"
                " OR lower(s.last_name || ' ' || s.first_name) LIKE ?"
                " OR lower(s.class_name) LIKE ?)"
            )
            params.extend([like, like, like])
        if class_name:
            clauses.append("s.class_name = ?")
            params.append(class_name)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT {', '.join('s.' + c for c in COLUMNS.split(', '))},"
            " COALESCE(SUM(p.amount), 0) AS paid"
            " FROM students s"
            " LEFT JOIN payments p ON p.student_id = s.id"
            f" {where}"
            " GROUP BY s.id"
            " ORDER BY s.last_name COLLATE NOCASE, s.first_name COLLATE NOCASE"
        )
        with self.db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [StudentAccount(student=row_to_student(row), total_paid=row["paid"]) for row in rows]

    def get_account(self, student_id: int) -> StudentAccount | None:
        """Élève + total réglé + historique complet des paiements."""
        student = self.get(student_id)
        if student is None:
            return None
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS paid FROM payments WHERE student_id = ?",
                (student_id,),
            ).fetchone()
        return StudentAccount(student=student, total_paid=rows["paid"])

    def list_classes(self) -> list[str]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT class_name FROM students ORDER BY class_name COLLATE NOCASE"
            ).fetchall()
        return [row["class_name"] for row in rows]

    def count(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
