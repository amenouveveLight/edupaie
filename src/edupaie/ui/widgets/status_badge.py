"""Badge de statut coloré (SOLDE / PARTIEL / NON_PAYE)."""

from PySide6.QtWidgets import QLabel

from edupaie.domain.enums import PaymentStatus


def repolish(widget) -> None:
    """Force Qt à réévaluer le QSS après un changement de propriété dynamique."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class StatusBadge(QLabel):
    def __init__(self, status: PaymentStatus | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("badge")
        if status is not None:
            self.set_status(status)

    def set_status(self, status: PaymentStatus) -> None:
        self.setText(status.label)
        self.setProperty("status", status.value)
        repolish(self)
