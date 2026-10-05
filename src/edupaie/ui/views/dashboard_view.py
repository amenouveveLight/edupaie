"""Vue « Tableau de bord » : indicateurs, répartition, derniers paiements, classes."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from edupaie.domain.enums import PaymentStatus
from edupaie.services.dashboard_service import DashboardService
from edupaie.ui.models import ClassSummaryModel, RecentPaymentsTableModel
from edupaie.ui.widgets import StatCard, StatusBadge
from edupaie.utils.formatting import format_fcfa


def _panel(title: str) -> tuple[QFrame, QTableView]:
    """Panneau blanc avec titre et tableau dedans."""
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)

    label = QLabel(title.upper())
    label.setObjectName("statTitle")
    layout.addWidget(label)

    table = QTableView()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(30)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    layout.addWidget(table)
    return frame, table


class DashboardView(QWidget):
    def __init__(self, dashboard_service: DashboardService, parent=None):
        super().__init__(parent)
        self._dashboard = dashboard_service
        self.setObjectName("page")

        # --- en-tête ---
        header = QVBoxLayout()
        title = QLabel("Tableau de bord")
        title.setObjectName("pageTitle")
        hint = QLabel("Vue d'ensemble des encaissements de l'école")
        hint.setObjectName("pageHint")
        header.addWidget(title)
        header.addWidget(hint)

        # --- cartes ---
        self.card_students = StatCard("Élèves inscrits")
        self.card_collected = StatCard("Total encaissé", tone="good")
        self.card_outstanding = StatCard("Reste à recouvrer", tone="warn")
        self.card_rate = StatCard("Taux de recouvrement", tone="good")

        cards = QHBoxLayout()
        cards.setSpacing(12)
        all_cards = (
            self.card_students,
            self.card_collected,
            self.card_outstanding,
            self.card_rate,
        )
        for card in all_cards:
            cards.addWidget(card, stretch=1)

        # --- répartition par statut ---
        self._status_labels: dict[PaymentStatus, QLabel] = {}
        status_row = QHBoxLayout()
        status_row.setSpacing(24)
        for status in (PaymentStatus.NON_PAYE, PaymentStatus.PARTIEL, PaymentStatus.SOLDE):
            frame = QFrame()
            row = QHBoxLayout(frame)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            row.addWidget(StatusBadge(status))
            count_label = QLabel("0 élève")
            count_label.setObjectName("infoMuted")
            row.addWidget(count_label)
            self._status_labels[status] = count_label
            status_row.addWidget(frame)
        status_row.addStretch(1)

        # --- panneaux ---
        recent_frame, self.recent_table = _panel("Derniers paiements")
        class_frame, self.class_table = _panel("Synthèse par classe")
        self.recent_model = RecentPaymentsTableModel()
        self.class_model = ClassSummaryModel()
        self.recent_table.setModel(self.recent_model)
        self.class_table.setModel(self.class_model)

        panels = QHBoxLayout()
        panels.setSpacing(12)
        panels.addWidget(recent_frame, stretch=3)
        panels.addWidget(class_frame, stretch=2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addLayout(cards)
        layout.addLayout(status_row)
        layout.addLayout(panels, stretch=1)

    def refresh(self) -> None:
        stats = self._dashboard.stats()
        self.card_students.set_value(str(stats.total_students))
        self.card_collected.set_value(format_fcfa(stats.total_collected))
        self.card_outstanding.set_value(format_fcfa(stats.outstanding))
        self.card_rate.set_value(f"{stats.collection_rate:.0%}")

        counts = {
            PaymentStatus.NON_PAYE: stats.count_non_paye,
            PaymentStatus.PARTIEL: stats.count_partiel,
            PaymentStatus.SOLDE: stats.count_solde,
        }
        for status, count in counts.items():
            self._status_labels[status].setText(f"{count} élève(s)")

        self.recent_model.set_rows(stats.recent_payments or [])
        self.class_model.set_rows(stats.per_class or [])
