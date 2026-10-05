"""Modèle de la liste des élèves (une ligne = StudentAccount)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from edupaie.domain.enums import PaymentStatus
from edupaie.domain.models import StudentAccount
from edupaie.services import balance
from edupaie.utils.formatting import format_fcfa

# Ordre d'affichage/tri du statut (les montants sont triés en entier, pas en texte)
_STATUS_RANK = {
    PaymentStatus.NON_PAYE: 1,
    PaymentStatus.PARTIEL: 2,
    PaymentStatus.SOLDE: 3,
}


class StudentsTableModel(QAbstractTableModel):
    HEADERS = ["Élève", "Classe", "Année", "Dû", "Payé", "Solde", "Statut"]

    def __init__(self, accounts: list[StudentAccount] | None = None, parent=None):
        super().__init__(parent)
        self._accounts: list[StudentAccount] = list(accounts or [])

    def set_accounts(self, accounts: list[StudentAccount]) -> None:
        self.beginResetModel()
        self._accounts = list(accounts)
        self.endResetModel()

    def account_at(self, row: int) -> StudentAccount | None:
        if 0 <= row < len(self._accounts):
            return self._accounts[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (API Qt)
        return 0 if parent.isValid() else len(self._accounts)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._accounts)):
            return None

        account = self._accounts[index.row()]
        student = account.student
        fee, paid = student.annual_fee, account.total_paid
        status = balance.derive_status(fee, paid)
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return [
                student.full_name,
                student.class_name,
                student.school_year,
                format_fcfa(fee),
                format_fcfa(paid),
                format_fcfa(balance.remaining(fee, paid)),
                status.label,
            ][col]

        if role == Qt.ItemDataRole.UserRole:  # valeur brute pour le tri
            return [
                student.full_name.lower(),
                student.class_name.lower(),
                student.school_year,
                fee,
                paid,
                balance.remaining(fee, paid),
                _STATUS_RANK[status],
            ][col]

        if role == Qt.ItemDataRole.TextAlignmentRole and col in (3, 4, 5):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
