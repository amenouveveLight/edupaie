"""Statistiques agrégées du tableau de bord."""

from dataclasses import dataclass
from datetime import date

from edupaie.data.repositories.payment_repository import PaymentRepository
from edupaie.data.repositories.student_repository import StudentRepository
from edupaie.domain.enums import PaymentStatus
from edupaie.domain.models import Payment
from edupaie.services import balance


@dataclass
class ClassSummary:
    class_name: str
    students: int
    collected: int
    outstanding: int


@dataclass
class DashboardStats:
    total_students: int = 0
    total_collected: int = 0
    collected_this_month: int = 0
    outstanding: int = 0
    total_due: int = 0
    count_solde: int = 0
    count_partiel: int = 0
    count_non_paye: int = 0
    # (paiement, nom complet de l'élève) — la vue n'a pas accès aux repositories
    recent_payments: list[tuple[Payment, str]] | None = None
    per_class: list[ClassSummary] | None = None

    @property
    def collection_rate(self) -> float:
        """Part des frais dus déjà encaissés (0.0 – 1.0)."""
        if self.total_due <= 0:
            return 1.0
        return max(0.0, min(1.0, (self.total_due - self.outstanding) / self.total_due))


class DashboardService:
    def __init__(self, students: StudentRepository, payments: PaymentRepository):
        self.students = students
        self.payments = payments

    def stats(self, recent_limit: int = 8) -> DashboardStats:
        accounts = self.students.list()
        stats = DashboardStats(total_students=len(accounts))
        names_by_id = {a.student.id: a.student.full_name for a in accounts}

        by_class: dict[str, ClassSummary] = {}
        for account in accounts:
            fee = account.student.annual_fee
            paid = account.total_paid
            stats.total_collected += paid
            stats.total_due += fee
            stats.outstanding += balance.remaining(fee, paid)

            status = balance.derive_status(fee, paid)
            if status is PaymentStatus.SOLDE:
                stats.count_solde += 1
            elif status is PaymentStatus.PARTIEL:
                stats.count_partiel += 1
            else:
                stats.count_non_paye += 1

            summary = by_class.setdefault(
                account.student.class_name,
                ClassSummary(account.student.class_name, 0, 0, 0),
            )
            summary.students += 1
            summary.collected += paid
            summary.outstanding += balance.remaining(fee, paid)

        today = date.today()
        stats.collected_this_month = self.payments.sum_between(
            today.replace(day=1).isoformat(),
            today.isoformat(),
        )
        stats.recent_payments = [
            (payment, names_by_id.get(payment.student_id, "Élève inconnu"))
            for payment in self.payments.recent(recent_limit)
        ]
        stats.per_class = sorted(by_class.values(), key=lambda c: c.class_name.lower())
        return stats
