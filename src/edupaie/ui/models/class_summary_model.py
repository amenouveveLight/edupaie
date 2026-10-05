"""Modèle « synthèse par classe » du tableau de bord."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from edupaie.services.dashboard_service import ClassSummary
from edupaie.utils.formatting import format_fcfa


class ClassSummaryModel(QAbstractTableModel):
    HEADERS = ["Classe", "Élèves", "Encaissé", "Reste dû"]

    def __init__(self, rows: list[ClassSummary] | None = None, parent=None):
        super().__init__(parent)
        self._rows: list[ClassSummary] = list(rows or [])

    def set_rows(self, rows: list[ClassSummary]) -> None:
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
        row = self._rows[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return [
                row.class_name,
                str(row.students),
                format_fcfa(row.collected),
                format_fcfa(row.outstanding),
            ][col]
        if role == Qt.ItemDataRole.UserRole:
            return [row.class_name.lower(), row.students, row.collected, row.outstanding][col]
        if role == Qt.ItemDataRole.TextAlignmentRole and col in (1, 2, 3):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None
