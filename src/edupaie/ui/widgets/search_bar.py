"""Barre de recherche réutilisable (champ à icône + effacement instantané)."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from edupaie.ui.icons import icon


class SearchBar(QWidget):
    """Champ de recherche dont `text_changed` alimente un QSortFilterProxyModel."""

    text_changed = Signal(str)

    def __init__(self, placeholder: str = "Rechercher...", parent=None):
        super().__init__(parent)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(placeholder)
        self.edit.setClearButtonEnabled(True)

        glyph = QLabel(self)
        pixmap = icon("search.svg").pixmap(16, 16)
        if not pixmap.isNull():
            glyph.setPixmap(pixmap)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(glyph)
        layout.addWidget(self.edit, stretch=1)

        self.edit.textChanged.connect(self.text_changed)

    def text(self) -> str:
        return self.edit.text()

    def set_focus(self) -> None:
        self.edit.setFocus()
