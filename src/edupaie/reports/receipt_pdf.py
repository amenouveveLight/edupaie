"""Génération PDF d'un reçu, à partir du snapshot figé (Receipt).

La date de création du PDF est figée à celle de l'émission : deux
réimpressions du même reçu produit des octets strictement identiques.

Le MÊME moteur de rendu accepte un ``Receipt`` (reçu final) ou un
``ReceiptDraft`` (aperçu). Pour un brouillon, un filigrane diagonal
« APERÇU – NON VALIDE » est ajouté et le numéro n'est pas affiché.

Sortie : fichier (generate_receipt_pdf → Path) ou octets en mémoire
(generate_receipt_pdf_bytes → bytes).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from edupaie.domain.models import Receipt, ReceiptDraft
from edupaie.utils.formatting import format_date, format_date_long, format_fcfa, latin1_safe

# Date de repli si le snapshot n'a pas d'horodatage (garantit la stabilité).
_FALLBACK_DATE = datetime(2026, 1, 1, 0, 0, 0)

PAGE_WIDTH = 148.0  # A5 en mm
PAGE_HEIGHT = 210.0
MARGIN = 14.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Palette (valeurs RGB)
NAVY = (30, 58, 95)
LIGHT = (240, 244, 248)
GREY = (110, 110, 110)
GREY_LIGHT = (180, 180, 180)  # pour le filigrane / caissier
GREEN = (30, 125, 70)

# Texte affiché à la place du numéro pour un brouillon.
PREVIEW_NUMBER = "Attribué à la validation"


def _issue_date(receipt: Receipt | ReceiptDraft) -> datetime:
    """Date de création du PDF, figée à l'horodatage du snapshot."""
    if receipt.issued_at:
        try:
            return datetime.fromisoformat(receipt.issued_at)
        except ValueError:
            pass
    return _FALLBACK_DATE


def _caissier(receipt: Receipt | ReceiptDraft) -> str:
    return getattr(receipt, "caissier", "") or ""


def _note(receipt: Receipt | ReceiptDraft) -> str:
    return getattr(receipt, "note", "") or ""


def _number_text(receipt: Receipt | ReceiptDraft, is_draft: bool) -> str:
    """Numéro à afficher : placeholder pour un brouillon, vrai numéro sinon."""
    if is_draft:
        return PREVIEW_NUMBER
    return receipt.number


def _add_watermark(pdf: FPDF) -> None:
    """Filigrane diagonal translucite « APERÇU – NON VALIDE »."""
    text = latin1_safe("APERÇU - NON VALIDE")
    with pdf.rotation(45, x=PAGE_WIDTH / 2, y=PAGE_HEIGHT / 2):
        pdf.set_font("helvetica", "B", 40)
        pdf.set_text_color(*GREY_LIGHT)
        tw = pdf.get_string_width(text)
        pdf.set_xy(PAGE_WIDTH / 2 - tw / 2, PAGE_HEIGHT / 2 - 12)
        pdf.cell(tw, 10, text, align="C")
    pdf.set_text_color(*NAVY)


def _render_core(pdf: FPDF, snap: Receipt | ReceiptDraft, is_draft: bool) -> None:
    """Moteur de rendu unifié : identique pour Receipt et ReceiptDraft.

    Pour un brouillon (is_draft=True), le filigrane est ajouté et le
    numéro affiché est le texte d'attente « Attribué à la validation ».
    """
    pdf.set_creation_date(_issue_date(snap))
    pdf.set_title(f"Reçu {_number_text(snap, is_draft)}")
    pdf.set_author("EduPaie")
    pdf.set_creator("EduPaie")
    pdf.set_auto_page_break(auto=True, margin=MARGIN)
    pdf.add_page()

    def line(text: str, size: float, style: str = "", color=NAVY, height: float = 6.0,
             new_y=YPos.NEXT, align="L", fill=False) -> None:
        pdf.set_font("helvetica", style, size)
        pdf.set_text_color(*color)
        pdf.cell(
            CONTENT_WIDTH, height, latin1_safe(text),
            new_x=XPos.LMARGIN, new_y=new_y, align=align, fill=fill,
        )

    def label_value(label: str, value: str, y_height: float = 7.0) -> None:
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*GREY)
        pdf.cell(52, y_height, latin1_safe(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, y_height, latin1_safe(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    caissier = _caissier(snap)
    note = _note(snap)

    # --- En-tête -------------------------------------------------------
    line("EduPaie", 20, "B")
    line("Reçu de paiement scolaire", 11, "", GREY, height=7)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.6)
    pdf.line(MARGIN, pdf.get_y() + 1.5, PAGE_WIDTH - MARGIN, pdf.get_y() + 1.5)
    pdf.ln(6)

    # --- Numéro de reçu (encadré) --------------------------------------
    pdf.set_fill_color(*LIGHT)
    pdf.set_draw_color(*LIGHT)
    pdf.rect(MARGIN, pdf.get_y(), CONTENT_WIDTH, 16, style="DF")
    pdf.set_xy(MARGIN, pdf.get_y() + 2)
    line("Reçu N°", 8, "", GREY, height=5, align="C")
    pdf.set_x(MARGIN)
    line(_number_text(snap, is_draft), 16, "B", NAVY, height=8, align="C")
    pdf.ln(8)

    # --- Identité ------------------------------------------------------
    label_value("Élève", snap.student_name)
    label_value("Classe", snap.class_name)
    label_value("Date du paiement", format_date(snap.paid_on))
    label_value("Mode de règlement", snap.mode.label)
    if caissier:
        label_value("Caissier", caissier)
    if note:
        label_value("Note", note)
    pdf.ln(3)

    # --- Montant -------------------------------------------------------
    pdf.set_fill_color(*LIGHT)
    pdf.rect(MARGIN, pdf.get_y(), CONTENT_WIDTH, 24, style="DF")
    pdf.set_xy(MARGIN, pdf.get_y() + 2.5)
    line("Montant payé", 9, "", GREY, height=5, align="C")
    pdf.set_x(MARGIN)
    line(format_fcfa(snap.amount), 18, "B", GREEN, height=9, align="C")
    pdf.ln(10)

    # --- Soldes (snapshot figé) ----------------------------------------
    label_value("Total déjà réglé", format_fcfa(snap.total_paid_after))
    balance_text = format_fcfa(snap.balance_after)
    if snap.balance_after < 0:
        balance_text = "Avance : " + format_fcfa(abs(snap.balance_after))
    label_value("Solde après paiement", balance_text)
    pdf.ln(4)

    # --- Pied de page --------------------------------------------------
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*GREY)
    pdf.multi_cell(
        CONTENT_WIDTH, 4,
        latin1_safe(
            f"Reçu émis le {format_date_long(_issue_date(snap))}. "
            "Ce document est un instantané figé : toute réimpression est identique. "
            "Merci de le conserver."
        ),
        align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )

    pdf.ln(6)
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(CONTENT_WIDTH / 2, 5, "Signature de l'école",
             new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
    pdf.cell(CONTENT_WIDTH / 2, 5, "Signature du parent",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    y = pdf.get_y() + 8
    pdf.set_draw_color(*GREY)
    pdf.set_line_width(0.3)
    pdf.line(MARGIN + 6, y, MARGIN + CONTENT_WIDTH / 2 - 6, y)
    pdf.line(MARGIN + CONTENT_WIDTH / 2 + 6, y, PAGE_WIDTH - MARGIN - 6, y)

    # --- Filigrane (après le contenu, au-dessus du rendu final) --------
    if is_draft:
        _add_watermark(pdf)


def _new_pdf() -> FPDF:
    """Crée une FPDF A5 prête à être rendue."""
    return FPDF(format=(PAGE_WIDTH, PAGE_HEIGHT), unit="mm")


def generate_receipt_pdf(receipt: Receipt, out_path: str | Path) -> Path:
    """Écrit le reçu en PDF et retourne le chemin du fichier.

    Préservé pour la compatibilité ascendante : accepte un Receipt (reçu final).
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = _new_pdf()
    _render_core(pdf, receipt, is_draft=False)
    pdf.output(str(out_path))
    return out_path


def generate_receipt_pdf_bytes(snap: Receipt | ReceiptDraft) -> bytes:
    """Génère le PDF en mémoire et retourne les octets bruts.

    Pour un ReceiptDraft, le rendu inclut le filigrane « APERÇU – NON VALIDE ».
    Pour un Receipt, le rendu est strictement identique à generate_receipt_pdf().
    """
    is_draft = isinstance(snap, ReceiptDraft)
    pdf = _new_pdf()
    _render_core(pdf, snap, is_draft=is_draft)
    # fpdf2 2.8.x : output() sans argument retourne un bytearray
    return bytes(pdf.output())
