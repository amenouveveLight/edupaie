"""Dialogue d'enregistrement d'un paiement.

Affiche le solde restant en direct et avertit (avec confirmation) si le
montant dépasse ce solde — c'est PaymentService qui tranche in fine.
"""

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from edupaie.domain.enums import PaymentMode
from edupaie.domain.exceptions import ValidationError
from edupaie.domain.models import StudentAccount
from edupaie.services import balance, validators
from edupaie.utils.formatting import format_fcfa

# Bouton principal : lance l'aperçu (le paiement n'est pas enregistré directement).
PREVIEW_BUTTON_TEXT = "Prévisualiser le reçu"

MAX_AMOUNT = 1_000_000_000


class PaymentDialog(QDialog):
    def __init__(
        self,
        account: StudentAccount,
        amount: int | None = None,
        mode: PaymentMode | None = None,
        paid_on: "date | None" = None,
        note: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._account = account
        self._remaining = balance.remaining(account.student.annual_fee, account.total_paid)

        self.setWindowTitle(f"Paiement — {account.student.full_name}")
        self.setMinimumWidth(420)

        student = account.student
        header = QLabel(
            f"<b>{student.full_name}</b> · {student.class_name}<br>"
            f"<span style='color:#6b7686'>Frais annuels : {format_fcfa(student.annual_fee)}"
            f" · Déjà réglé : {format_fcfa(account.total_paid)}</span>",
            self,
        )
        header.setTextFormat(Qt.TextFormat.RichText)

        self.solde_label = QLabel(f"Solde restant : {format_fcfa(self._remaining)}", self)
        self.solde_label.setObjectName("soldeBig")
        self.solde_label.setStyleSheet("color: #1e3a5f;")

        self.amount = QLineEdit(self)
        self.amount.setPlaceholderText("Montant en FCFA")
        self.amount.setValidator(QIntValidator(1, MAX_AMOUNT, self.amount))

        self.mode = QComboBox(self)
        for mode in PaymentMode:
            self.mode.addItem(mode.label, mode)

        self.paid_on = QDateEdit(self)
        self.paid_on.setCalendarPopup(True)
        self.paid_on.setDisplayFormat("dd/MM/yyyy")
        self.paid_on.setDate(QDate.currentDate())
        self.paid_on.setMaximumDate(QDate.currentDate())

        self.note = QLineEdit(self)
        self.note.setPlaceholderText("Facultatif (ex. 2e tranche, numéro de transaction...)")

        self.preview = QLabel(self)
        self.preview.setObjectName("infoMuted")

        self.warning = QLabel(self)
        self.warning.setObjectName("warning")
        self.warning.setWordWrap(True)
        self.warning.hide()

        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Montant *", self.amount)
        form.addRow("Mode *", self.mode)
        form.addRow("Date *", self.paid_on)
        form.addRow("Note", self.note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(PREVIEW_BUTTON_TEXT)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("variant", "primary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(header)
        layout.addWidget(self.solde_label)
        layout.addLayout(form)
        layout.addWidget(self.preview)
        layout.addWidget(self.warning)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

        self.amount.textChanged.connect(self._update_preview)
        self._update_preview()
        self.amount.setFocus()

        # Pré-remplissage (pour le retour via « Modifier » depuis l'aperçu).
        if amount is not None:
            self.amount.setText(str(amount))
        if mode is not None:
            idx = self.mode.findData(mode)
            if idx >= 0:
                self.mode.setCurrentIndex(idx)
        if paid_on is not None:
            qdate = QDate(paid_on.year, paid_on.month, paid_on.day)
            self.paid_on.setDate(qdate)
        if note:
            self.note.setText(note)

    # --- état ----------------------------------------------------------

    @property
    def amount_value(self) -> int:
        return int(self.amount.text() or 0)

    @property
    def mode_value(self) -> PaymentMode:
        return self.mode.currentData()

    @property
    def paid_on_value(self) -> date:
        return self.paid_on.date().toPython()

    @property
    def note_value(self) -> str:
        return self.note.text().strip()

    def _update_preview(self) -> None:
        text = self.amount.text().strip()
        if not text:
            self.preview.setText("")
            self.warning.hide()
            return
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.preview.setText("")
            self.warning.setText("Le montant doit être un nombre entier supérieur à 0.")
            self.warning.show()
            return

        solde_apres = self._remaining - amount
        if solde_apres >= 0:
            self.preview.setText(f"Solde après paiement : {format_fcfa(solde_apres)}")
            self.warning.hide()
        else:
            self.preview.setText("")
            self.warning.setText(
                f"Attention : ce montant dépasse le solde restant "
                f"({format_fcfa(self._remaining)}) de {format_fcfa(-solde_apres)}."
            )
            self.warning.show()

    # --- validation ----------------------------------------------------

    def accept(self) -> None:
        try:
            amount = validators.validate_amount(self.amount.text())
        except ValidationError as exc:
            QMessageBox.warning(self, "Montant invalide", str(exc))
            return

        solde_apres = self._remaining - amount
        if solde_apres < 0:
            QMessageBox.warning(
                self,
                "Solde dépassé",
                f"Ce montant dépasserait le solde restant de {format_fcfa(-solde_apres)}.\n\n"
                "Un paiement ne peut jamais rendre le solde négatif : "
                "réduisez le montant saisi.",
            )
            self.amount.setFocus()
            self.amount.selectAll()
            return

        super().accept()
