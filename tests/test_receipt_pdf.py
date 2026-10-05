"""Génération PDF du reçu (fpdf2) : fichier valide, snapshot respecté."""

from edupaie.reports.receipt_pdf import generate_receipt_pdf


def test_generate_receipt_pdf(payment_service, make_student, tmp_path):
    student = make_student(annual_fee=50000)
    _, receipt = payment_service.register(student.id, 20000, "ESPECES", "2026-10-01")

    out = tmp_path / "recu.pdf"
    result = generate_receipt_pdf(receipt, out)

    assert result == out
    assert out.exists()
    content = out.read_bytes()
    assert content.startswith(b"%PDF")
    assert len(content) > 1000


def test_reprint_is_byte_identical(payment_service, make_student, tmp_path):
    """La réimpression d'un snapshot produit strictement le même PDF."""
    student = make_student(annual_fee=50000)
    _, receipt = payment_service.register(student.id, 20000, "ESPECES", "2026-10-01")

    first = generate_receipt_pdf(receipt, tmp_path / "a.pdf").read_bytes()
    second = generate_receipt_pdf(receipt, tmp_path / "b.pdf").read_bytes()
    assert first == second
