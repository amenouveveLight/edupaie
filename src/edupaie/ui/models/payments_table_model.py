"""Modèle de l'historique des paiements d'un élève."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from edupaie.domain.models import Payment
from edupaie.utils.formatting import format_date, format_fcfa


class PaymentsTableModel(QAbstractTableModel):
    HEADERS = ["Date", "Montant", "Mode", "Note"]

    def __init__(self, payments: list[Payment] | None = None, parent=None):
        super().__init__(parent)
        self._payments: list[Payment] = list(payments or [])

    def set_payments(self, payments: list[Payment]) -> None:
        self.beginResetModel()
        self._payments = list(payments)
        self.endResetModel()

    def payment_at(self, row: int) -> Payment | None:
        if 0 <= row < len(self._payments):
            return self._payments[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._payments)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._payments)):
            return None

        payment = self._payments[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return [
                format_date(payment.paid_on),
                format_fcfa(payment.amount),
                payment.mode.label,
                payment.note or "—",
            ][col]

        if role == Qt.ItemDataRole.UserRole:
            return [
                payment.paid_on,  # ISO => tri chronologique
                payment.amount,
                payment.mode.label,
                payment.note,
            ][col]

        if role == Qt.ItemDataRole.TextAlignmentRole and col == 1:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
