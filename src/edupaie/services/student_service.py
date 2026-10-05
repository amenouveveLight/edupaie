"""Service élèves : CRUD + règles métier (ex. suppression interdite si paiements)."""

from __future__ import annotations

from datetime import datetime

from edupaie.data.repositories.payment_repository import PaymentRepository
from edupaie.data.repositories.student_repository import StudentRepository
from edupaie.domain.enums import PaymentStatus
from edupaie.domain.exceptions import NotFoundError, ValidationError
from edupaie.domain.models import Payment, Student, StudentAccount
from edupaie.services import balance, validators


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class StudentService:
    def __init__(self, students: StudentRepository, payments: PaymentRepository):
        self.students = students
        self.payments = payments

    # --- CRUD ----------------------------------------------------------

    def create(self, first_name, last_name, class_name, annual_fee,
               school_year=None, guardian_phone="", email="") -> Student:
        data = validators.validate_student(
            first_name, last_name, class_name, annual_fee,
            school_year=school_year, guardian_phone=guardian_phone, email=email,
        )
        now = _now()
        student = Student(**data, created_at=now, updated_at=now)
        return self.students.add(student)

    def update(self, student: Student) -> Student:
        if student.id is None:
            raise ValidationError("Élève sans identifiant : mise à jour impossible.")
        if self.students.get(student.id) is None:
            raise NotFoundError(f"Élève introuvable (id {student.id}).")
        data = validators.validate_student(
            student.first_name, student.last_name, student.class_name,
            student.annual_fee, school_year=student.school_year,
            guardian_phone=student.guardian_phone, email=student.email,
        )
        updated = Student(**data, id=student.id, created_at=student.created_at, updated_at=_now())
        return self.students.update(updated)

    def delete(self, student_id: int) -> None:
        """Suppression refusée si l'élève a déjà des paiements (traçabilité)."""
        if self.students.get(student_id) is None:
            raise NotFoundError(f"Élève introuvable (id {student_id}).")
        if self.payments.total_for_student(student_id) > 0:
            raise ValidationError(
                "Impossible de supprimer cet élève : il a déjà des paiements enregistrés."
            )
        self.students.delete(student_id)

    # --- lectures ------------------------------------------------------

    def get(self, student_id: int) -> Student:
        student = self.students.get(student_id)
        if student is None:
            raise NotFoundError(f"Élève introuvable (id {student_id}).")
        return student

    def account(self, student_id: int) -> StudentAccount:
        account = self.students.get_account(student_id)
        if account is None:
            raise NotFoundError(f"Élève introuvable (id {student_id}).")
        return account

    def list(self, search: str = "", class_name: str | None = None,
             status: PaymentStatus | str | None = None) -> list[StudentAccount]:
        """Liste filtrée : recherche et classe en SQL, statut via la règle métier."""
        wanted = PaymentStatus(status) if isinstance(status, str) and status else status
        accounts = self.students.list(search=search, class_name=class_name)
        if wanted:
            accounts = [
                a for a in accounts
                if balance.derive_status(a.student.annual_fee, a.total_paid) == wanted
            ]
        return accounts

    def classes(self) -> list[str]:
        return self.students.list_classes()

    def payments_of(self, student_id: int) -> list[Payment]:
        """Historique complet d'un élève (les règles de suppression restent ici)."""
        self.get(student_id)  # lève NotFoundError si absent
        return self.payments.list_for_student(student_id)
