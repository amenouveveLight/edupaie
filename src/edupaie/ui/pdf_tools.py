"""Génération et ouverture d'un reçu PDF depuis l'interface."""

import logging
import tempfile
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from edupaie import config
from edupaie.domain.models import Receipt, ReceiptDraft
from edupaie.reports.receipt_pdf import generate_receipt_pdf, generate_receipt_pdf_bytes

logger = logging.getLogger("edupaie.ui")


def receipt_pdf_path(receipt: Receipt) -> Path:
    return config.RECEIPT_DIR / f"{receipt.number}.pdf"


def open_receipt(receipt: Receipt) -> Path:
    """(Ré)génère le PDF du reçu depuis son snapshot, puis l'ouvre."""
    path = generate_receipt_pdf(receipt, receipt_pdf_path(receipt))
    logger.info("Reçu ouvert : %s", path)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    return path


def preview_bytes(snap: Receipt | ReceiptDraft) -> bytes:
    """Génère le PDF d'aperçu en mémoire (bytes)."""
    return generate_receipt_pdf_bytes(snap)


def save_temp_pdf(data: bytes, suffix: str = ".pdf") -> str:
    """Écrit des octets PDF dans un fichier temporaire et retourne son chemin.

    Le fichier est créé avec delete=False ; l'appelant est responsable de le
    supprimer (via cleanup_temp_pdf)."""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="edupaie_preview_")
    with open(fd, "wb") as f:
        f.write(data)
    return path


def cleanup_temp_pdf(path: str) -> None:
    """Supprime un fichier PDF temporaire, en ignorant les erreurs."""
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
