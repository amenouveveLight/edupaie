"""Règles de calcul du solde. Solde = dû − Σ paiements ; le statut en est dérivé.

Ces fonctions sont pures (entiers en FCFA, zéro I/O) : faciles à tester.
"""

from edupaie.domain.enums import PaymentStatus
from edupaie.domain.models import Payment, Student


def total_paid(payments: list[Payment]) -> int:
    return sum(p.amount for p in payments)


def balance_of(annual_fee: int, paid: int) -> int:
    """Solde restant dû. Peut être négatif si un surpaiement a été accepté."""
    return annual_fee - paid


def remaining(annual_fee: int, paid: int) -> int:
    """Solde affiché/plafonné à 0 (on ne doit jamais « devoir » -5 000 FCFA)."""
    return max(balance_of(annual_fee, paid), 0)


def derive_status(annual_fee: int, paid: int) -> PaymentStatus:
    """Statut dérivé, jamais stocké."""
    if paid >= annual_fee:
        return PaymentStatus.SOLDE  # y compris dû 0, payé 0 : rien à régler
    if paid <= 0:
        return PaymentStatus.NON_PAYE
    return PaymentStatus.PARTIEL


def student_balance(student: Student, payments: list[Payment]) -> int:
    return balance_of(student.annual_fee, total_paid(payments))


def student_status(student: Student, payments: list[Payment]) -> PaymentStatus:
    return derive_status(student.annual_fee, total_paid(payments))
