"""Repositories : SQL, filtres, intégrité référentielle, cascades."""

import sqlite3

import pytest

from edupaie.domain.models import Student


def test_student_crud(students):
    now = "2026-10-01T08:00:00"
    student = students.add(
        Student(
            first_name="Kal", last_name="Koné", class_name="5ème B",
            annual_fee=75000, created_at=now, updated_at=now,
        )
    )
    assert student.id is not None

    fetched = students.get(student.id)
    assert fetched is not None
    assert fetched.full_name == "KONÉ Kal"
    assert fetched.annual_fee == 75000

    fetched.annual_fee = 80000
    fetched.updated_at = "2026-10-02T09:00:00"
    students.update(fetched)
    assert students.get(student.id).annual_fee == 80000

    students.delete(student.id)
    assert students.get(student.id) is None


def test_get_returns_none_for_unknown(students):
    assert students.get(4242) is None


def test_list_search_and_class_filter(student_service):
    student_service.create("Awa", "Diallo", "6ème A", 50000)
    student_service.create("Kal", "Koné", "5ème B", 60000)
    student_service.create("Moussa", "Traoré", "6ème A", 70000)

    assert len(student_service.list()) == 3
    assert [a.student.first_name for a in student_service.list(search="diallo")] == ["Awa"]
    assert [a.student.first_name for a in student_service.list(search="moussa")] == ["Moussa"]
    assert len(student_service.list(class_name="6ème A")) == 2
    assert len(student_service.list(search="6ème", class_name="6ème A")) == 2


def test_list_returns_totals_paid(student_service, payment_service):
    student = student_service.create("Awa", "Diallo", "6ème A", 50000)
    payment_service.register(student.id, 20000, "ESPECES", "2026-10-01")
    payment_service.register(student.id, 5000, "ESPECES", "2026-10-02")

    accounts = student_service.list()
    assert len(accounts) == 1
    assert accounts[0].total_paid == 25000


def test_list_classes_is_sorted_and_distinct(student_service):
    student_service.create("A", "Un", "6ème A", 0)
    student_service.create("B", "Deux", "5ème B", 0)
    student_service.create("C", "Trois", "6ème A", 0)
    assert student_service.classes() == ["5ème B", "6ème A"]


def test_payment_totals_and_date_range(payment_service, make_student, payments):
    student = make_student(annual_fee=100000)
    payment_service.register(student.id, 10000, "ESPECES", "2026-09-15")
    payment_service.register(student.id, 20000, "ESPECES", "2026-10-01")

    assert payments.total_for_student(student.id) == 30000
    assert payments.sum_between("2026-10-01", "2026-10-31") == 20000
    assert payments.sum_between("2026-09-01", "2026-09-30") == 10000
    assert payments.sum_between("2026-11-01", "2026-11-30") == 0
    assert payments.count() == 2


def test_foreign_key_enforced(db, payments):
    from edupaie.domain.enums import PaymentMode
    from edupaie.domain.models import Payment

    with pytest.raises(sqlite3.IntegrityError):
        bad = Payment(
            student_id=9999, amount=1000, mode=PaymentMode.ESPECES, paid_on="2026-10-01"
        )
        with db.transaction() as conn:
            payments.insert(conn, bad)


def test_delete_student_cascades_payments(
    student_service, db, payments, make_student, payment_service
):
    student = make_student(annual_fee=1000)
    payment_service.register(student.id, 1000, "ESPECES", "2026-10-01")

    # Les reçus référencent encore le paiement : on vide d'abord les snapshots.
    with db.transaction() as conn:
        conn.execute("DELETE FROM receipts")
    student_service.students.delete(student.id)

    assert student_service.list() == []
    assert payments.count() == 0


def test_receipt_snapshot_survives_student_rename(student_service, payment_service, make_student):
    """Le reçu garde le nom du jour de l'émission, même après changement."""
    student = make_student(annual_fee=50000)
    _, receipt = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")

    student.last_name = "NOM_MODIFIÉ"
    student_service.update(student)

    from_db = payment_service.receipts.get(receipt.id)
    assert from_db.student_name == "DIALLO Awa"
