"""Numérotation des reçus : séquence annuelle unique, jamais consommée deux fois."""

import sqlite3
from datetime import datetime

import pytest

from edupaie.domain.models import PaymentMode


def test_sequential_numbers_within_current_year(payment_service, make_student):
    student = make_student(annual_fee=200000)
    year = datetime.now().year

    _, first = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    _, second = payment_service.register(student.id, 10000, "ESPECES", "2026-10-02")

    assert first.number == f"REC-{year}-000001"
    assert second.number == f"REC-{year}-000002"
    assert first.number != second.number


def test_counter_independent_per_year(db, receipts):
    """Chaque année a sa propre séquence (REC-2025-000001, REC-2026-000001...)."""
    with db.transaction() as conn:
        n_2025 = receipts.next_number(conn, 2025)
        n_2025_bis = receipts.next_number(conn, 2025)
        n_2026 = receipts.next_number(conn, 2026)
    assert n_2025 == "REC-2025-000001"
    assert n_2025_bis == "REC-2025-000002"
    assert n_2026 == "REC-2026-000001"


def test_rollback_does_not_consume_number(db, receipts):
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            number = receipts.next_number(conn, 2026)
            raise RuntimeError("échec simulé après numérotation")
    assert number == "REC-2026-000001"  # numéro consommé... mais rollback

    with db.transaction() as conn:
        retry = receipts.next_number(conn, 2026)
    assert retry == "REC-2026-000001"  # ...et réutilisé : aucun trou


def test_duplicate_number_rejected_by_database(payment_service, make_student, receipts):
    student = make_student(annual_fee=100000)
    _, receipt1 = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    _, receipt2 = payment_service.register(student.id, 10000, "ESPECES", "2026-10-02")

    receipt2.number = receipt1.number  # tentative de falsification / double émission
    with pytest.raises(sqlite3.IntegrityError):
        with payment_service.db.transaction() as conn:
            receipts.insert(conn, receipt2)


def test_receipt_stored_with_its_number(payment_service, make_student, receipt_service):
    student = make_student(annual_fee=100000)
    _, receipt = payment_service.register(student.id, 25000, "MOBILE_MONEY", "2026-10-01")

    fetched = receipt_service.get_by_number(receipt.number)
    assert fetched.id == receipt.id
    assert fetched.amount == 25000
    assert fetched.mode is PaymentMode.MOBILE_MONEY
