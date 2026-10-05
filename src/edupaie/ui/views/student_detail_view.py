"""Vue « Fiche élève » : solde, historique, encaissement, réimpression des reçus."""

from __future__ import annotations

import logging

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from edupaie.domain.exceptions import EduPaieError, NotFoundError, OverpaymentError
from edupaie.domain.models import Receipt, StudentAccount
from edupaie.services import PaymentService, ReceiptService, StudentService, balance
from edupaie.ui.dialogs import PaymentDialog, ReceiptPreviewDialog
from edupaie.ui.icons import icon
from edupaie.ui.models import PaymentsTableModel
from edupaie.ui.widgets import StatCard, StatusBadge, repolish
from edupaie.utils.formatting import format_fcfa

logger = logging.getLogger("edupaie.ui")


class StudentDetailView(QWidget):
    """Fiche d'un élève. Émet back_requested quand il faut revenir à la liste."""

    back_requested = Signal()
    edit_requested = Signal(int)

    def __init__(
        self,
        student_service: StudentService,
        payment_service: PaymentService,
        receipt_service: ReceiptService,
        parent=None,
    ):
        super().__init__(parent)
        self._students = student_service
        self._payments = payment_service
        self._receipts = receipt_service
        self._student_id: int | None = None
        self.setObjectName("page")

        # --- navigation ---
        self.btn_back = QPushButton(" ← Retour à la liste", self)
        self.btn_back.setProperty("variant", "flat")
        nav = QHBoxLayout()
        nav.addWidget(self.btn_back)
        nav.addStretch(1)

        # --- identité ---
        self.title = QLabel("—")
        self.title.setObjectName("pageTitle")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("pageHint")
        self.badge = StatusBadge()
        identity = QHBoxLayout()
        identity.addWidget(self.title, stretch=1)
        identity.addWidget(self.badge)

        # --- soldes ---
        self.card_due = StatCard("Frais annuels")
        self.card_paid = StatCard("Total réglé", tone="good")
        self.card_balance = StatCard("Solde restant")
        cards = QHBoxLayout()
        cards.setSpacing(12)
        for card in (self.card_due, self.card_paid, self.card_balance):
            cards.addWidget(card, stretch=1)

        # --- actions ---
        self.btn_payment = QPushButton(" Nouveau paiement", self)
        self.btn_payment.setProperty("variant", "primary")
        self.btn_payment.setIcon(icon("payment.svg"))
        self.btn_edit = QPushButton(" Modifier la fiche", self)
        self.btn_edit.setIcon(icon("edit.svg"))
        self.btn_receipt = QPushButton(" Ouvrir le dernier reçu", self)
        self.btn_receipt.setIcon(icon("print.svg"))
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.btn_payment)
        actions.addWidget(self.btn_edit)
        actions.addWidget(self.btn_receipt)
        actions.addStretch(1)

        # --- historique ---
        history_title = QLabel("Historique des paiements")
        history_title.setObjectName("statTitle")
        self.history_model = PaymentsTableModel()
        self.history_proxy = QSortFilterProxyModel(self)
        self.history_proxy.setSourceModel(self.history_model)
        self.history_proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.history_table = QTableView()
        self.history_table.setModel(self.history_proxy)
        self.history_table.setSortingEnabled(True)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.verticalHeader().setDefaultSectionSize(32)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.doubleClicked.connect(self._open_receipt_for_row)

        self.empty_label = QLabel("Aucun paiement enregistré pour le moment.")
        self.empty_label.setObjectName("infoMuted")

        # --- mise en page ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addLayout(nav)
        layout.addLayout(identity)
        layout.addWidget(self.subtitle)
        layout.addLayout(cards)
        layout.addLayout(actions)
        layout.addWidget(history_title)
        layout.addWidget(self.history_table, stretch=1)
        layout.addWidget(self.empty_label)

        self.btn_back.clicked.connect(self.back_requested)
        self.btn_edit.clicked.connect(lambda: self.edit_requested.emit(self._student_id or 0))
        self.btn_payment.clicked.connect(self._on_new_payment)
        self.btn_receipt.clicked.connect(self._open_last_receipt)

    # --- chargement ----------------------------------------------------

    def load(self, student_id: int) -> None:
        self._student_id = student_id
        self.refresh()

    def refresh(self) -> None:
        if self._student_id is None:
            return
        try:
            account = self._students.account(self._student_id)
            payments = self._students.payments_of(self._student_id)
        except NotFoundError:
            self.back_requested.emit()
            return

        student = account.student
        fee, paid = student.annual_fee, account.total_paid
        status = balance.derive_status(fee, paid)

        self.title.setText(student.full_name)
        details = [student.class_name]
        if student.school_year:
            details.append(f"Année {student.school_year}")
        if student.guardian_phone:
            details.append(f"Tuteur : {student.guardian_phone}")
        if student.email:
            details.append(student.email)
        self.subtitle.setText(" · ".join(details))
        self.badge.set_status(status)

        self.card_due.set_value(format_fcfa(fee))
        self.card_paid.set_value(format_fcfa(paid))
        balance_value = balance.balance_of(fee, paid)
        if balance_value > 0:
            self.card_balance.set_value(format_fcfa(balance_value))
            self.card_balance.setProperty("tone", "warn")
        elif balance_value < 0:
            self.card_balance.set_value(f"Avance {format_fcfa(abs(balance_value))}")
            self.card_balance.setProperty("tone", "good")
        else:
            self.card_balance.set_value(format_fcfa(0))
            self.card_balance.setProperty("tone", "good")
        repolish(self.card_balance)

        self.history_model.set_payments(payments)
        self.history_table.resizeColumnsToContents()
        self.empty_label.setVisible(not payments)
        self.history_table.setVisible(bool(payments))
        self.btn_receipt.setEnabled(bool(payments))

    # --- actions -------------------------------------------------------

    def _on_new_payment(self) -> None:
        """Nouveau paiement : PaymentDialog → preview → ReceiptPreviewDialog → register."""
        if self._student_id is None:
            return
        try:
            account = self._students.account(self._student_id)
        except NotFoundError:
            self.back_requested.emit()
            return

        # Boucle : l'utilisateur peut revenir via « Modifier » ou relancer l'aperçu
        # si le solde a changé entre-temps.
        self._payment_preview_flow(account)

    def _payment_preview_flow(
        self, account: StudentAccount, previous: dict | None = None
    ) -> None:
        """Flow : PaymentDialog (valeurs préservées) → preview → dialog de confirmation."""
        kwargs = {
            "amount": previous["amount"] if previous else None,
            "mode": previous["mode"] if previous else None,
            "paid_on": previous["paid_on"] if previous else None,
            "note": previous["note"] if previous else None,
        }
        dialog = PaymentDialog(account, parent=self, **kwargs)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        params = {
            "amount": dialog.amount_value,
            "mode": dialog.mode_value,
            "paid_on": dialog.paid_on_value,
            "note": dialog.note_value,
        }
        self._show_preview(account, params)

    def _show_preview(self, account: StudentAccount, params: dict) -> None:
        """Affiche l'aperçu du reçu, puis gère confirmation / modification / erreur."""
        student_id = account.student.id
        amount = params["amount"]
        mode = params["mode"]
        paid_on = params["paid_on"]
        note = params["note"]

        # --- preview (lecture seule, zéro écriture) ---
        try:
            draft = self._payments.preview(
                student_id=student_id,
                amount=amount,
                mode=mode,
                paid_on=paid_on,
                note=note,
            )
        except OverpaymentError as exc:
            QMessageBox.warning(self, "Surpaiement", str(exc))
            return
        except EduPaieError as exc:
            QMessageBox.warning(self, "Erreur", str(exc))
            return

        # --- dialog de confirmation ---
        def do_register() -> tuple:
            return self._payments.register(
                student_id=student_id,
                amount=amount,
                mode=mode,
                paid_on=paid_on,
                note=note,
            )

        preview_dialog = ReceiptPreviewDialog(draft, register_fn=do_register, parent=self)

        # Confirmation réussie → enregistrer et rafraîchir
        def on_confirmed(_payment, receipt):
            self.refresh()
            QMessageBox.information(
                self,
                "Paiement enregistré",
                f"Paiement de {format_fcfa(_payment.amount)} enregistré.\n"
                f"Reçu {receipt.number} créé.",
            )
            # Afficher le reçu final (sans filigrane) avec boutons Imprimer/Enregistrer
            final_dialog = ReceiptPreviewDialog(receipt, parent=self)
            final_dialog.exec()

        # Erreur pendant register (ex. solde changé entre-temps) → relancer l'aperçu
        def on_error(exc):
            if isinstance(exc, OverpaymentError):
                QMessageBox.warning(self, "Surpaiement", str(exc))
            else:
                QMessageBox.critical(self, "Erreur", str(exc))
            # Re-générer l'aperçu avec les données actualisées
            self._show_preview(account, params)

        # « Modifier » → retourner au formulaire avec les valeurs conservées
        def on_modify():
            self._payment_preview_flow(account, previous=params)

        preview_dialog.confirmed.connect(on_confirmed)
        preview_dialog.confirmError.connect(on_error)
        preview_dialog.modifyRequested.connect(on_modify)
        preview_dialog.exec()

    def _selected_payment_id(self) -> int | None:
        selection = self.history_table.selectionModel()
        indexes = selection.selectedRows() if selection else []
        if not indexes:
            return None
        payment = self.history_model.payment_at(self.history_proxy.mapToSource(indexes[0]).row())
        return payment.id if payment else None

    def _open_receipt_for_row(self, proxy_index: QModelIndex) -> None:
        payment = self.history_model.payment_at(self.history_proxy.mapToSource(proxy_index).row())
        if payment is None:
            return
        receipt = self._receipts.find_for_payment(payment.id)
        if receipt is None:
            QMessageBox.information(
                self, "Reçu introuvable",
                "Aucun reçu n'est associé à ce paiement.",
            )
            return
        self._open_receipt(receipt)

    def _open_last_receipt(self) -> None:
        if self._student_id is None:
            return
        receipts = self._receipts.list_for_student(self._student_id)
        if not receipts:
            QMessageBox.information(self, "Aucun reçu", "Aucun reçu à réimprimer.")
            return
        self._open_receipt(receipts[0])  # le plus récent

    def _open_receipt(self, receipt: Receipt) -> None:
        """Affiche un reçu existant dans le dialogue d'aperçu (sans filigrane)."""
        try:
            dialog = ReceiptPreviewDialog(receipt, parent=self)
            dialog.exec()
            logger.info("Reçu ouvert : %s", receipt.number)
        except Exception:
            logger.exception("Échec d'ouverture du reçu %s", receipt.number)
            QMessageBox.critical(
                self, "Erreur",
                "Impossible de générer le PDF du reçu.",
            )
