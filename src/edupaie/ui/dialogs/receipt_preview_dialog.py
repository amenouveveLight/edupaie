"""Dialogue modal d'aperçu d'un reçu (nouveau ou existant).

Affiche le PDF dans un QPdfView (QtPdfWidgets) — ou un QPixmap de secours
si QtPdf n'est pas disponible — avec des boutons adaptés au mode :

* **Brouillon** (ReceiptDraft) : « Modifier » / « Confirmer et générer » / « Annuler ».
  Le bouton Confirmer est désactivé pendant l'appel à ``register_fn`` pour
  éviter les doubles clics.
* **Reçu existant** (Receipt) : « Imprimer » / « Enregistrer » / « Fermer »,
  sans filigrane, généré depuis le snapshot.

Le PDF est généré en mémoire (bytes) puis stocké dans un fichier temporaire
supprimé à la fermeture — jamais dans le dossier des reçus.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from edupaie.domain.models import Receipt, ReceiptDraft
from edupaie.ui.pdf_tools import cleanup_temp_pdf, preview_bytes, save_temp_pdf

logger = logging.getLogger("edupaie.ui")

# QtPdfWidgets est optionnel : secours par QPixmap si absent.
try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView

    _HAS_QTPDF = True
except ImportError:  # pragma: no cover - environnement sans QtPdf
    _HAS_QTPDF = False

# Alias pour generate_receipt_pdf_bytes déjà importé depuis pdf_tools.
# (pdf_tools.generate_receipt_pdf_bytes redirige vers reports.receipt_pdf.)


class _PdfViewer(QWidget):
    """Contenu PDF : QPdfView si disponible, sinon QPixmap de secours."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._temp_path: str | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        if _HAS_QTPDF:
            self._view = QPdfView(self)
            self._view.setPageMode(QPdfView.PageMode.SinglePage)
            self._view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self._doc: QPdfDocument | None = None
            self._pixmap_label: QLabel | None = None
        else:
            self._view = None
            self._pixmap_label = QLabel(self)
            self._pixmap_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(self._pixmap_label)
            self._doc = None

    def set_pdf_bytes(self, data: bytes) -> None:
        """Affiche le PDF depuis des octets en mémoire."""
        self._temp_path = save_temp_pdf(data)
        if _HAS_QTPDF and self._view is not None:
            self._doc = QPdfDocument()
            self._doc.load(self._temp_path)
            self._view.setDocument(self._doc)
            self._layout.addWidget(self._view)
        else:
            # Secours : render la première page en pixmap via QPdfDocument.render
            # (non disponible sans QtPdf) → on indique simplement le chargement.
            # Dans la pratique, QtPdf est requis par PySide6 >= 6.5.
            self._pixmap_label.setText(
                "visualisation PDF indisponible (QtPdf manquant)."
            )

    def cleanup(self) -> None:
        """Libère les ressources et supprime le fichier temporaire."""
        if self._doc is not None:
            self._doc.close()
            self._doc = None
        if self._temp_path:
            cleanup_temp_pdf(self._temp_path)
            self._temp_path = None


class ReceiptPreviewDialog(QDialog):
    """Aperçu modal d'un reçu.

    Mode brouillon (draft=True) : 3 boutons — Modifier / Confirmer / Annuler.
    Mode reçu final (draft=False) : 3 boutons — Imprimer / Enregistrer / Fermer.

    Signaux :
        confirmed  – émis quand register_fn réussit, avec (payment, receipt)
        confirmError – émis quand register_fn lève une exception
        modifyRequested – émis quand l'utilisateur clique sur « Modifier »
    """

    confirmed = Signal(object, object)  # (Payment, Receipt)
    confirmError = Signal(object)       # Exception
    modifyRequested = Signal()

    # Codes de retour
    RESULT_MODIFY = 2

    def __init__(
        self,
        snap: Receipt | ReceiptDraft,
        register_fn: Callable[[], tuple] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._snap = snap
        self._register_fn = register_fn
        self._is_draft = isinstance(snap, ReceiptDraft)

        self.setWindowTitle(
            "Aperçu du reçu" if self._is_draft else f"Reçu {snap.number}"
        )
        self.setModal(True)
        self.setMinimumSize(600, 700)

        # --- contenu PDF ---
        self._viewer = _PdfViewer(self)
        data = preview_bytes(snap)
        self._viewer.set_pdf_bytes(data)

        # --- titre — sous-titre ---
        title = "Aperçu du reçu (non valide)" if self._is_draft else f"Reçu {snap.number}"
        subtitle = (
            "Vérifiez les informations, puis confirmez ou modifiez."
            if self._is_draft
            else "Reçu déjà émis — vous pouvez l'imprimer ou l'enregistrer."
        )
        title_label = QLabel(f"<b>{title}</b>", self)
        subtitle_label = QLabel(subtitle, self)
        subtitle_label.setObjectName("pageHint")

        # --- boutons ---
        self._btn_print = QPushButton(" Imprimer", self)
        self._btn_print.setIcon(_icon("print.svg"))
        self._btn_save = QPushButton(" Enregistrer", self)
        self._btn_save.setIcon(_icon("save.svg"))
        self._btn_modify = QPushButton(" Modifier", self)
        self._btn_modify.setProperty("variant", "outline")
        self._btn_confirm = QPushButton(" Confirmer et générer", self)
        self._btn_confirm.setProperty("variant", "primary")
        self._btn_cancel = QPushButton(" Annuler", self)
        self._btn_cancel.setProperty("variant", "outline")

        if self._is_draft:
            # Mode brouillon : Modifier / Confirmer / Annuler
            self._btn_modify.setVisible(True)
            self._btn_confirm.setVisible(True)
            self._btn_cancel.setVisible(True)
            self._btn_print.setVisible(False)
            self._btn_save.setVisible(False)
        else:
            # Mode reçu existant : Imprimer / Enregistrer / Fermer
            self._btn_modify.setVisible(False)
            self._btn_confirm.setVisible(False)
            self._btn_cancel.setVisible(True)
            self._btn_cancel.setText(" Fermer")
            self._btn_print.setVisible(True)
            self._btn_save.setVisible(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        if not self._is_draft:
            btn_row.addWidget(self._btn_print)
            btn_row.addWidget(self._btn_save)
        if self._is_draft:
            btn_row.addWidget(self._btn_modify)
            btn_row.addWidget(self._btn_confirm)
        btn_row.addWidget(self._btn_cancel)

        # --- layout ---
        layout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(self._viewer, stretch=1)
        layout.addLayout(btn_row)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- connexions ---
        self._btn_cancel.clicked.connect(self.reject)
        if self._is_draft:
            self._btn_modify.clicked.connect(self._on_modify)
            self._btn_confirm.clicked.connect(self._on_confirm)
        else:
            self._btn_print.clicked.connect(self._on_print)
            self._btn_save.clicked.connect(self._on_save)

    # --- actions ---

    def _on_modify(self) -> None:
        """L'utilisateur veut revenir au formulaire de paiement."""
        self.modifyRequested.emit()
        self.reject()

    def _on_confirm(self) -> None:
        """L'utilisateur confirme : appeler register_fn (protection double-clic)."""
        if self._register_fn is None:
            return
        self._btn_confirm.setEnabled(False)
        self._btn_modify.setEnabled(False)
        try:
            payment, receipt = self._register_fn()
        except Exception as exc:
            self._btn_confirm.setEnabled(True)
            self._btn_modify.setEnabled(True)
            self.confirmError.emit(exc)
            return
        self.confirmed.emit(payment, receipt)
        self.accept()

    def _on_print(self) -> None:
        """Imprime le reçu existant via QDesktopServices."""
        from edupaie.ui.pdf_tools import open_receipt

        if isinstance(self._snap, Receipt):
            try:
                open_receipt(self._snap)
            except Exception:
                QMessageBox.critical(self, "Erreur", "Impossible d'imprimer le reçu.")
        else:
            QMessageBox.information(
                self, "Info",
                "Utilisez 'Enregistrer' puis imprimez le fichier.",
            )

    def _on_save(self) -> None:
        """Enregistre le PDF du reçu dans un fichier choisi par l'utilisateur."""
        from PySide6.QtWidgets import QFileDialog

        from edupaie.reports.receipt_pdf import generate_receipt_pdf
        from edupaie.ui.pdf_tools import receipt_pdf_path

        if isinstance(self._snap, Receipt):
            path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer le reçu",
                str(receipt_pdf_path(self._snap)),
                "PDF (*.pdf)",
            )
            if path:
                try:
                    generate_receipt_pdf(self._snap, path)
                    QMessageBox.information(self, "Enregistré", f"Reçu enregistré : {path}")
                except Exception:
                    QMessageBox.critical(self, "Erreur", "Impossible d'enregistrer le reçu.")
        else:
            # Brouillon : on peut aussi enregistrer l'aperçu
            path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer l'aperçu", "", "PDF (*.pdf)",
            )
            if path:
                data = preview_bytes(self._snap)
                with open(path, "wb") as f:
                    f.write(data)
                QMessageBox.information(self, "Enregistré", f"Aperçu enregistré : {path}")

    # --- lifecycle ---

    def reject(self) -> None:
        self._viewer.cleanup()
        super().reject()

    def accept(self) -> None:
        self._viewer.cleanup()
        super().accept()


def _icon(name: str):
    """Charge une icône depuis le thème/icons, retourne None si indisponible."""
    try:
        from edupaie.ui.icons import icon
        return icon(name)
    except Exception:
        return None
