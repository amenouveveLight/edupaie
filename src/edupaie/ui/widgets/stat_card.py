"""Carte de statistique du tableau de bord."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", tone: str = "default", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setProperty("tone", tone)

        self.title_label = QLabel(title.upper(), self)
        self.title_label.setObjectName("statTitle")
        self.value_label = QLabel(value, self)
        self.value_label.setObjectName("statValue")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
