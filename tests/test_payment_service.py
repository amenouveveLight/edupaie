"""PaymentService : validation, refus de surpaiement, transaction tout-ou-rien."""

import pytest

from edupaie.domain.exceptions import NotFoundError, OverpaymentError, ValidationError


def test_register_creates_payment_and_receipt(payment_service, students, make_student):
    student = make_student(annual_fee=50000)
    payment, receipt = payment_service.register(
        student.id, 20000, "ESPECES", "2026-10-01", note="1re tranche"
    )

    assert payment.id is not None and receipt.id is not None
    assert payment.amount == 20000
    assert payment.note == "1re tranche"
    # Snapshot du reçu : solde après = 50000 − 20000
    assert receipt.total_paid_after == 20000
    assert receipt.balance_after == 30000
    assert receipt.student_name == "DIALLO Awa"
    assert receipt.class_name == "6ème A"
    # Persistance
    assert payment_service.payments.total_for_student(student.id) == 20000
    assert payment_service.receipts.count() == 1


def test_register_all_payment_modes(payment_service, make_student):
    student = make_student(annual_fee=100000)
    for mode in ["ESPECES", "MOBILE_MONEY", "VIREMENT", "CHEQUE"]:
        _, receipt = payment_service.register(student.id, 10000, mode, "2026-10-01")
        assert receipt.mode.value == mode
    assert payment_service.receipts.count() == 4


@pytest.mark.parametrize("bad_amount", [0, -500, "abc", 12.5, None])
def test_amount_must_be_positive_integer(payment_service, make_student, bad_amount):
    student = make_student()
    with pytest.raises(ValidationError):
        payment_service.register(student.id, bad_amount, "ESPECES", "2026-10-01")
    assert payment_service.payments.count() == 0


def test_unknown_student_raises_not_found(payment_service):
    with pytest.raises(NotFoundError):
        payment_service.register(999, 10000, "ESPECES", "2026-10-01")
    assert payment_service.payments.count() == 0


def test_invalid_date_or_mode_rejected(payment_service, make_student):
    student = make_student()
    with pytest.raises(ValidationError):
        payment_service.register(student.id, 10000, "ESPECES", "31/02/2026")
    with pytest.raises(ValidationError):
        payment_service.register(student.id, 10000, "BITCOIN", "2026-10-01")
    assert payment_service.payments.count() == 0


def test_overpayment_rejected_and_nothing_persisted(payment_service, make_student, db):
    student = make_student(annual_fee=50000)
    with pytest.raises(OverpaymentError):
        payment_service.register(student.id, 60000, "ESPECES", "2026-10-01")

    assert payment_service.payments.count() == 0
    assert payment_service.receipts.count() == 0
    # Le compteur n'a pas été consommé : le prochain reçu reste REC-...-000001
    _, receipt = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    assert receipt.number.endswith("-000001")


def test_overpayment_always_refused_even_for_one_unit(payment_service, make_student):
    """Règle du sujet : le solde ne passe JAMAIS sous 0, aucune exception."""
    student = make_student(annual_fee=50000)
    payment_service.register(student.id, 50000, "ESPECES", "2026-10-01")
    with pytest.raises(OverpaymentError):
        payment_service.register(student.id, 1, "ESPECES", "2026-10-02")
    assert payment_service.payments.count() == 1


def test_exact_solde_closes_account(payment_service, make_student, student_service):
    student = make_student(annual_fee=30000)
    payment_service.register(student.id, 30000, "VIREMENT", "2026-10-01")
    account = student_service.account(student.id)
    assert account.total_paid == 30000

    with pytest.raises(OverpaymentError):
        payment_service.register(student.id, 1, "ESPECES", "2026-10-02")


def test_transaction_rolls_back_everything_on_failure(
    payment_service, make_student, db, monkeypatch
):
    """Si la création du reçu échoue, ni le paiement ni le numéro ne subsistent."""
    student = make_student(annual_fee=50000)
    receipts_repo = payment_service.receipts

    def boom(conn, receipt):
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(receipts_repo, "insert", boom)
    with pytest.raises(RuntimeError):
        payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    monkeypatch.undo()

    assert payment_service.payments.count() == 0
    assert payment_service.receipts.count() == 0
    with db.connection() as conn:
        row = conn.execute("SELECT value FROM receipt_counter").fetchone()
    assert row is None  # compteur jamais incrémenté

    _, receipt = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    assert receipt.number.endswith("-000001")
