"""Fenêtre principale : barre latérale + QStackedWidget (bord, liste, fiche)."""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from edupaie import __version__
from edupaie.domain.exceptions import NotFoundError, ValidationError
from edupaie.services import DashboardService, PaymentService, ReceiptService, StudentService
from edupaie.ui.dialogs import StudentFormDialog
from edupaie.ui.icons import icon
from edupaie.ui.views import DashboardView, StudentDetailView, StudentsView
from edupaie.ui.widgets import repolish

logger = logging.getLogger("edupaie.ui")

PAGE_DASHBOARD = 0
PAGE_STUDENTS = 1
PAGE_DETAIL = 2


class MainWindow(QMainWindow):
    def __init__(
        self,
        student_service: StudentService,
        payment_service: PaymentService,
        receipt_service: ReceiptService,
        dashboard_service: DashboardService,
    ):
        super().__init__()
        self._students = student_service

        self.setWindowTitle("EduPaie — Gestion des paiements scolaires")
        self.resize(1240, 780)
        self.setMinimumSize(1000, 640)
        self.setWindowIcon(icon("app.svg"))

        # --- barre latérale ---
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 14, 0, 18)
        side_layout.setSpacing(2)

        app_title = QLabel("EduPaie")
        app_title.setObjectName("appTitle")
        app_subtitle = QLabel("Paiements scolaires")
        app_subtitle.setObjectName("appSubtitle")
        side_layout.addWidget(app_title)
        side_layout.addWidget(app_subtitle)

        self.nav_buttons: list[QPushButton] = []
        for label, page, ic in (
            ("Tableau de bord", PAGE_DASHBOARD, "dashboard.svg"),
            ("Élèves", PAGE_STUDENTS, "students.svg"),
        ):
            button = QPushButton(f"  {label}", self)
            button.setObjectName("navButton")
            button.setIcon(icon(ic))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, p=page: self.show_page(p))
            side_layout.addWidget(button)
            self.nav_buttons.append(button)

        side_layout.addStretch(1)
        version = QLabel(f"EduPaie v{__version__}")
        version.setObjectName("appSubtitle")
        side_layout.addWidget(version)

        # --- pages ---
        self.stack = QStackedWidget()
        self.dashboard = DashboardView(dashboard_service)
        self.students_view = StudentsView(student_service, payment_service)
        self.detail_view = StudentDetailView(student_service, payment_service, receipt_service)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.students_view)
        self.stack.addWidget(self.detail_view)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

        # --- navigation entre vues ---
        self.students_view.open_student.connect(self.show_student)
        self.detail_view.back_requested.connect(self.back_to_students)
        self.detail_view.edit_requested.connect(self._edit_from_detail)

        self.show_page(PAGE_DASHBOARD)

    # --- navigation ----------------------------------------------------

    def show_page(self, page: int) -> None:
        if page == PAGE_DASHBOARD:
            self.dashboard.refresh()
        elif page == PAGE_STUDENTS:
            self.students_view.refresh()
        self.stack.setCurrentIndex(page)
        self._update_nav(page)

    def _update_nav(self, page: int) -> None:
        active = PAGE_STUDENTS if page == PAGE_DETAIL else page
        for index, button in enumerate(self.nav_buttons):
            button.setProperty("active", index == active)
            repolish(button)

    def show_student(self, student_id: int) -> None:
        """Ouvre la fiche d'un élève (depuis la liste ou après création)."""
        self.detail_view.load(student_id)
        self.stack.setCurrentIndex(PAGE_DETAIL)
        self._update_nav(PAGE_DETAIL)

    def back_to_students(self) -> None:
        self.show_page(PAGE_STUDENTS)

    # --- édition depuis la fiche ---------------------------------------

    def _edit_from_detail(self, student_id: int) -> None:
        try:
            student = self._students.get(student_id)
        except NotFoundError:
            self.back_to_students()
            return

        dialog = StudentFormDialog(student, self._students.classes(), parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.cleaned_data()
        student.first_name = data["first_name"]
        student.last_name = data["last_name"]
        student.class_name = data["class_name"]
        student.school_year = data["school_year"]
        student.annual_fee = data["annual_fee"]
        student.guardian_phone = data["guardian_phone"]
        student.email = data["email"]
        try:
            self._students.update(student)
        except ValidationError as exc:
            QMessageBox.warning(self, "Formulaire invalide", str(exc))
            return

        self.detail_view.refresh()
        self.students_view.refresh()
        self.dashboard.refresh()
