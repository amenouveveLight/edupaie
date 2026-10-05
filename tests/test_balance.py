"""Règles pures : solde = dû − Σ paiements, statut dérivé."""

from edupaie.domain.enums import PaymentStatus
from edupaie.domain.models import Payment, Student
from edupaie.services import balance


def _student(fee):
    return Student(first_name="Kal", last_name="Koné", class_name="5ème B", annual_fee=fee)


def _payment(amount):
    return Payment(student_id=1, amount=amount, mode="ESPECES", paid_on="2026-10-01")  # type: ignore[arg-type]


def test_balance_is_fee_minus_payments():
    assert balance.balance_of(50000, 0) == 50000
    assert balance.balance_of(50000, 20000) == 30000
    assert balance.balance_of(50000, 50000) == 0


def test_balance_can_go_negative_on_overpayment():
    assert balance.balance_of(50000, 60000) == -10000


def test_remaining_is_clamped_to_zero():
    assert balance.remaining(50000, 60000) == 0
    assert balance.remaining(50000, 45000) == 5000


def test_total_paid_sums_payments():
    assert balance.total_paid([_payment(10000), _payment(15000), _payment(5000)]) == 30000
    assert balance.total_paid([]) == 0


def test_status_non_paye_partiel_solde():
    assert balance.derive_status(50000, 0) is PaymentStatus.NON_PAYE
    assert balance.derive_status(50000, 1) is PaymentStatus.PARTIEL
    assert balance.derive_status(50000, 49999) is PaymentStatus.PARTIEL
    assert balance.derive_status(50000, 50000) is PaymentStatus.SOLDE
    assert balance.derive_status(50000, 99999) is PaymentStatus.SOLDE  # surpayé => soldé


def test_status_with_no_fee_defined_is_solde():
    assert balance.derive_status(0, 0) is PaymentStatus.SOLDE


def test_student_helpers():
    student = _student(40000)
    payments = [_payment(10000), _payment(20000)]
    assert balance.student_balance(student, payments) == 10000
    assert balance.student_status(student, payments) is PaymentStatus.PARTIEL
