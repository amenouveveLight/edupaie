"""Vue « Élèves » : recherche, filtres classe/statut, CRUD, double-clic = fiche."""

from __future__ import annotations

import logging

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
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

from edupaie.domain.enums import PaymentStatus
from edupaie.domain.exceptions import NotFoundError, ValidationError
from edupaie.services import PaymentService, StudentService
from edupaie.ui.dialogs import StudentFormDialog
from edupaie.ui.icons import icon
from edupaie.ui.models import StudentsTableModel
from edupaie.ui.widgets import SearchBar

logger = logging.getLogger("edupaie.ui")


class StudentsView(QWidget):
    """Liste des élèves. Émet open_student(id) quand une fiche doit s'ouvrir."""

    open_student = Signal(int)

    def __init__(self, student_service: StudentService, payment_service: PaymentService,
                 parent=None):
        super().__init__(parent)
        self._students = student_service
        self._payments = payment_service
        self.setObjectName("page")

        # --- en-tête et barre d'outils ---
        title = QLabel("Élèves")
        title.setObjectName("pageTitle")
        hint = QLabel("Recherchez, filtrez, puis double-cliquez pour ouvrir une fiche")
        hint.setObjectName("pageHint")

        self.search = SearchBar("Rechercher un élève, une classe...")
        self.class_filter = QComboBox()
        self.class_filter.setMinimumWidth(150)
        self.status_filter = QComboBox()
        self.status_filter.setMinimumWidth(140)
        self._fill_filters()

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addWidget(self.search, stretch=1)
        toolbar.addWidget(self.class_filter)
        toolbar.addWidget(self.status_filter)

        # --- table ---
        self.model = StudentsTableModel()
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(Qt.ItemDataRole.UserRole)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self._on_double_click)

        self.count_label = QLabel("")
        self.count_label.setObjectName("infoMuted")

        # --- actions ---
        self.btn_add = QPushButton(" Ajouter un élève", self)
        self.btn_add.setProperty("variant", "primary")
        self.btn_add.setIcon(icon("add.svg"))
        self.btn_edit = QPushButton(" Modifier", self)
        self.btn_edit.setIcon(icon("edit.svg"))
        self.btn_delete = QPushButton(" Supprimer", self)
        self.btn_delete.setProperty("variant", "danger")
        self.btn_delete.setIcon(icon("delete.svg"))

        actions = QHBoxLayout()
        actions.addWidget(self.count_label)
        actions.addStretch(1)
        actions.addWidget(self.btn_edit)
        actions.addWidget(self.btn_delete)
        actions.addWidget(self.btn_add)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_delete.clicked.connect(self._on_delete)
        self.search.text_changed.connect(lambda _t: self.refresh())
        self.class_filter.currentIndexChanged.connect(lambda _i: self.refresh())
        self.status_filter.currentIndexChanged.connect(lambda _i: self.refresh())

        # --- mise en page ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(actions)

        self.refresh()

    # --- données -------------------------------------------------------

    def _fill_filters(self) -> None:
        self.class_filter.addItem("Toutes les classes", None)
        for name in self._students.classes():
            self.class_filter.addItem(name, name)

        self.status_filter.addItem("Tous les statuts", None)
        for status in PaymentStatus:
            self.status_filter.addItem(status.label, status.value)

    def refresh(self) -> None:
        class_name = self.class_filter.currentData()
        status = self.status_filter.currentData()
        accounts = self._students.list(
            search=self.search.text(), class_name=class_name, status=status
        )
        self.model.set_accounts(accounts)
        n = len(accounts)
        self.count_label.setText(f"{n} élève{'s' if n > 1 else ''}")
        has_selection = self._selected_account() is not None
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _selected_account(self):
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not indexes:
            return None
        source_index = self.proxy.mapToSource(indexes[0])
        return self.model.account_at(source_index.row())

    def _on_double_click(self, proxy_index: QModelIndex) -> None:
        account = self.model.account_at(self.proxy.mapToSource(proxy_index).row())
        if account and account.student.id is not None:
            self.open_student.emit(account.student.id)

    # --- actions -------------------------------------------------------

    def _on_add(self) -> None:
        dialog = StudentFormDialog(classes=self._students.classes(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            student = self._students.create(**dialog.cleaned_data())
        except ValidationError as exc:
            QMessageBox.warning(self, "Formulaire invalide", str(exc))
            return
        self._refresh_filters()
        self.refresh()
        logger.info("Élève créé : %s", student.full_name)
        self.open_student.emit(student.id)

    def _on_edit(self) -> None:
        account = self._selected_account()
        if account is None:
            return
        dialog = StudentFormDialog(account.student, self._students.classes(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = account.student
            data = dialog.cleaned_data()
            updated.first_name = data["first_name"]
            updated.last_name = data["last_name"]
            updated.class_name = data["class_name"]
            updated.school_year = data["school_year"]
            updated.annual_fee = data["annual_fee"]
            updated.guardian_phone = data["guardian_phone"]
            updated.email = data["email"]
            self._students.update(updated)
        except ValidationError as exc:
            QMessageBox.warning(self, "Formulaire invalide", str(exc))
            return
        self._refresh_filters()
        self.refresh()

    def _on_delete(self) -> None:
        account = self._selected_account()
        if account is None:
            return
        answer = QMessageBox.question(
            self,
            "Supprimer l'élève",
            f"Supprimer définitivement {account.student.full_name} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._students.delete(account.student.id)
        except (ValidationError, NotFoundError) as exc:
            QMessageBox.information(self, "Suppression impossible", str(exc))
            return
        self._refresh_filters()
        self.refresh()

    def _refresh_filters(self) -> None:
        current_class = self.class_filter.currentData()
        self.class_filter.blockSignals(True)
        self.class_filter.clear()
        self.class_filter.addItem("Toutes les classes", None)
        for name in self._students.classes():
            self.class_filter.addItem(name, name)
        index = self.class_filter.findData(current_class)
        self.class_filter.setCurrentIndex(max(index, 0))
        self.class_filter.blockSignals(False)
