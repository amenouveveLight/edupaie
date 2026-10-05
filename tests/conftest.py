"""Fixtures : une base SQLite isolée par test, des services assemblés à la main.

Aucun Qt n'est importé ici — toute la couche métier est testable en tête seule.
La base est un fichier dans tmp_path (et non :memory:) car chaque connexion
SQLite mémoire est indépendante, alors que nos repositories ouvrent et ferment
leurs connexions.
"""

import pytest

from edupaie import config
from edupaie.data.database import Database
from edupaie.data.migrator import Migrator
from edupaie.data.repositories import PaymentRepository, ReceiptRepository, StudentRepository
from edupaie.services import DashboardService, PaymentService, ReceiptService, StudentService


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    Migrator(database, config.MIGRATIONS_DIR).migrate()
    return database


@pytest.fixture
def students(db):
    return StudentRepository(db)


@pytest.fixture
def payments(db):
    return PaymentRepository(db)


@pytest.fixture
def receipts(db):
    return ReceiptRepository(db)


@pytest.fixture
def student_service(students, payments):
    return StudentService(students, payments)


@pytest.fixture
def payment_service(db, students, payments, receipts):
    return PaymentService(db, students, payments, receipts)


@pytest.fixture
def receipt_service(receipts):
    return ReceiptService(receipts)


@pytest.fixture
def dashboard_service(students, payments):
    return DashboardService(students, payments)


@pytest.fixture
def make_student(student_service):
    """Fabrique d'élèves : make_student() puis make_student(annual_fee=75000)..."""

    def _make(
        first_name="Awa", last_name="Diallo", class_name="6ème A", annual_fee=50000, **kwargs
    ):
        return student_service.create(
            first_name=first_name,
            last_name=last_name,
            class_name=class_name,
            annual_fee=annual_fee,
            **kwargs,
        )

    return _make
