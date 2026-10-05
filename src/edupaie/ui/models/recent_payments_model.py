"""Modèle « derniers paiements » du tableau de bord (paiement + nom de l'élève)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from edupaie.domain.models import Payment
from edupaie.utils.formatting import format_date, format_fcfa


class RecentPaymentsTableModel(QAbstractTableModel):
    HEADERS = ["Date", "Élève", "Montant", "Mode"]

    def __init__(self, rows: list[tuple[Payment, str]] | None = None, parent=None):
        super().__init__(parent)
        self._rows: list[tuple[Payment, str]] = list(rows or [])

    def set_rows(self, rows: list[tuple[Payment, str]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        payment, student_name = self._rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return [
                format_date(payment.paid_on),
                student_name,
                format_fcfa(payment.amount),
                payment.mode.label,
            ][col]
        if role == Qt.ItemDataRole.UserRole:
            return [payment.paid_on, student_name.lower(), payment.amount, payment.mode.label][col]
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 2:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
