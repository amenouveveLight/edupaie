"""Tests du feature 'prévisualisation du reçu avant génération'.

Aucun Qt n'est nécessaire : on teste PaymentService.preview(), generate_receipt_pdf_bytes,
et la non-consommation du compteur de numéros.
"""

from __future__ import annotations

import re
import zlib

import pytest

from edupaie.domain.exceptions import OverpaymentError
from edupaie.domain.models import ReceiptDraft
from edupaie.reports.receipt_pdf import generate_receipt_pdf, generate_receipt_pdf_bytes

# --------------------------------------------------------------------------- #
# preview() : zéro écriture, zéro consommation de numéro
# --------------------------------------------------------------------------- #

def test_preview_writes_nothing(payment_service, make_student):
    """preview() ne crée aucun paiement, aucun reçu, et ne touche pas le compteur."""
    student = make_student(annual_fee=50000)

    payment_service.preview(student.id, 20000, "ESPECES", "2026-10-01", note="1re tranche")

    assert payment_service.payments.count() == 0
    assert payment_service.receipts.count() == 0

    # Le compteur n'a jamais été incrémenté → le premier reçu réel vient REC-...-000001.
    _, receipt = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    assert receipt.number.endswith("-000001")


def test_preview_does_not_consume_counter_even_on_error(payment_service, make_student):
    """Des aperçus annulés ne sautent aucun numéro de séquence."""
    student = make_student(annual_fee=100000)

    # Trois aperçus (annulés, aucune écriture)
    for _ in range(3):
        payment_service.preview(student.id, 10000, "ESPECES", "2026-10-01")

    # Puis un vrai enregistrement → le numéro est 000001, rien n'a été sauté.
    _, receipt = payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")
    assert receipt.number.endswith("-000001")


def test_preview_overpayment_raises(payment_service, make_student):
    """Si amount > solde, preview() lève OverpaymentError AVANT aucune écriture."""
    student = make_student(annual_fee=50000)

    with pytest.raises(OverpaymentError):
        payment_service.preview(student.id, 60000, "ESPECES", "2026-10-01")

    assert payment_service.payments.count() == 0
    assert payment_service.receipts.count() == 0


# --------------------------------------------------------------------------- #
# preview() : valeurs identiques au reçu émis par register()
# --------------------------------------------------------------------------- #

def test_preview_values_match_register(payment_service, make_student):
    """total_paid_after / balance_after de preview() == celles de register()."""
    student = make_student(annual_fee=50000)
    amount, mode, paid_on, note = 20000, "ESPECES", "2026-10-01", "1re tranche"

    draft = payment_service.preview(student.id, amount, mode, paid_on, note)

    _, receipt = payment_service.register(student.id, amount, mode, paid_on, note)

    assert draft.total_paid_after == receipt.total_paid_after
    assert draft.balance_after == receipt.balance_after
    assert draft.student_name == receipt.student_name
    assert draft.class_name == receipt.class_name
    assert draft.amount == receipt.amount
    assert draft.mode.value == receipt.mode.value
    assert draft.paid_on == receipt.paid_on
    assert draft.caissier == receipt.caissier
    assert draft.note == receipt.note


def test_preview_returns_receipt_draft(payment_service, make_student):
    """Le type retourné par preview() est bien un ReceiptDraft."""
    student = make_student(annual_fee=50000)

    draft = payment_service.preview(student.id, 20000, "ESPECES", "2026-10-01")

    assert isinstance(draft, ReceiptDraft)
    assert draft.number == "Attribué à la validation"


# --------------------------------------------------------------------------- #
# PDF : filigrane + absence de numéro pour un brouillon
# --------------------------------------------------------------------------- #

def test_draft_pdf_has_watermark_and_no_real_number(payment_service, make_student):
    """Le PDF d'un brouillon contient le filigrane et pas de numéro définitif."""
    student = make_student(annual_fee=50000)

    draft = payment_service.preview(student.id, 20000, "ESPECES", "2026-10-01")

    pdf_bytes = generate_receipt_pdf_bytes(draft)
    assert pdf_bytes.startswith(b"%PDF")
    text = _extract_text(pdf_bytes)

    # Filigrane présent (les mots clefs sont en ASCII pur)
    assert "NON VALIDE" in text

    # Le numéro réel REC-... n'apparaît pas
    assert "REC-" not in text

    # Le texte d'attente est affiché
    assert "Attribu" in text  # "Attribué à la validation" passé par latin1_safe


def test_draft_pdf_same_layout_as_final_receipt(payment_service, make_student):
    """Le PDF du brouillon et du reçu final doivent avoir la même structure visuelle."""
    student = make_student(annual_fee=50000)

    # Brouillon
    draft = payment_service.preview(
        student.id, 20000, "ESPECES", "2026-10-01", note="tranche 1"
    )
    draft_text = _extract_text(generate_receipt_pdf_bytes(draft))

    # Reçu final (register avec les mêmes entrées)
    _, receipt = payment_service.register(
        student.id, 20000, "ESPECES", "2026-10-01", note="tranche 1"
    )
    final_text = _extract_text(generate_receipt_pdf_bytes(receipt))

    # Mêmes montants, élève, note, etc.
    assert "20 000 FCFA" in draft_text
    assert "20 000 FCFA" in final_text
    assert "DIALLO" in draft_text
    assert "DIALLO" in final_text
    assert "tranche 1" in draft_text
    assert "tranche 1" in final_text
    # Le filigrane est uniquement dans le brouillon
    assert "NON VALIDE" in draft_text
    assert "NON VALIDE" not in final_text


def test_reprint_final_receipt_is_byte_identical(payment_service, make_student, tmp_path):
    """La réimpression d'un reçu final produit des octets strictement identiques."""
    student = make_student(annual_fee=50000)
    _, receipt = payment_service.register(student.id, 20000, "ESPECES", "2026-10-01")

    # Par generate_receipt_pdf (chemin fichier)
    first_file = generate_receipt_pdf(receipt, tmp_path / "a.pdf").read_bytes()
    second_file = generate_receipt_pdf(receipt, tmp_path / "b.pdf").read_bytes()

    # Par generate_receipt_pdf_bytes (mémoire)
    third_bytes = generate_receipt_pdf_bytes(receipt)

    assert first_file == second_file
    assert first_file == third_bytes


def test_draft_pdf_does_not_appear_in_receipt_directory(payment_service, make_student):
    """Un aperçu ne doit jamais créer de fichier dans le dossier des reçus."""
    from pathlib import Path

    from edupaie import config

    student = make_student(annual_fee=50000)

    # S'assurer que le dossier des reçus est vide avant
    receipt_dir = Path(config.RECEIPT_DIR)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    before = set(receipt_dir.glob("*.pdf"))

    draft = payment_service.preview(student.id, 20000, "ESPECES", "2026-10-01")
    generate_receipt_pdf_bytes(draft)

    after = set(receipt_dir.glob("*.pdf"))
    assert before == after


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _extract_text(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF en décompressant ses flux avec zlib (sans dépendance)."""
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.DOTALL)
    chunks: list[bytes] = []
    for raw in streams:
        try:
            chunks.append(zlib.decompress(raw))
        except zlib.error:
            continue
    # Décoder en latin-1 pour préserver les caractères du PDF (0-255).
    return b"\n".join(chunks).decode("latin-1", errors="replace")
