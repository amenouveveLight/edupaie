"""Dialogue de création / modification d'une fiche élève.

Le dialogue n'impose que le format (via validators, couche services) ; les
règles métier restent dans les services.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from edupaie.domain.exceptions import ValidationError
from edupaie.domain.models import Student
from edupaie.services import validators
from edupaie.utils.formatting import current_school_year

MAX_AMOUNT = 1_000_000_000


class StudentFormDialog(QDialog):
    def __init__(self, student: Student | None = None, classes: list[str] | None = None,
                 parent=None):
        super().__init__(parent)
        self._student = student
        self._cleaned: dict | None = None

        self.setWindowTitle("Modifier l'élève" if student else "Nouvel élève")
        self.setMinimumWidth(420)

        self.first_name = QLineEdit(student.first_name if student else "")
        self.last_name = QLineEdit(student.last_name if student else "")
        self.class_name = QLineEdit(student.class_name if student else "")
        self.class_name.setPlaceholderText("ex. 6ème A")
        if classes:
            class_completer = QCompleter(classes, self.class_name)
            class_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.class_name.setCompleter(class_completer)

        initial_year = (
            student.school_year if student and student.school_year else current_school_year()
        )
        self.school_year = QLineEdit(initial_year)
        self.school_year.setPlaceholderText("ex. 2026-2027")
        self.school_year.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d{4}-\d{4}"), self.school_year)
        )

        self.annual_fee = QLineEdit(str(student.annual_fee) if student else "")
        self.annual_fee.setPlaceholderText("ex. 50000 (FCFA)")
        self.annual_fee.setValidator(QIntValidator(0, MAX_AMOUNT, self.annual_fee))

        self.guardian_phone = QLineEdit(student.guardian_phone if student else "")
        self.guardian_phone.setPlaceholderText("+225 07 00 00 00")
        self.email = QLineEdit(student.email if student else "")
        self.email.setPlaceholderText("parent@exemple.ci")

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(10)
        form.addRow("Prénom *", self.first_name)
        form.addRow("Nom *", self.last_name)
        form.addRow("Classe *", self.class_name)
        form.addRow("Année scolaire *", self.school_year)
        form.addRow("Frais annuels *", self.annual_fee)
        form.addRow("Téléphone du tuteur", self.guardian_phone)
        form.addRow("E-mail", self.email)

        hint = QLabel("Les champs marqués * sont obligatoires.", self)
        hint.setObjectName("infoMuted")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

        self.first_name.setFocus()

    def cleaned_data(self) -> dict:
        """Données validées et nettoyées, disponibles après accept()."""
        assert self._cleaned is not None
        return self._cleaned

    def accept(self) -> None:
        try:
            self._cleaned = validators.validate_student(
                self.first_name.text(),
                self.last_name.text(),
                self.class_name.text(),
                self.annual_fee.text(),
                school_year=self.school_year.text(),
                guardian_phone=self.guardian_phone.text(),
                email=self.email.text(),
            )
        except ValidationError as exc:
            QMessageBox.warning(self, "Formulaire invalide", str(exc))
            return
        super().accept()
