"""Point de composition : DB → migrations → repositories → services → UI."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from edupaie import config
from edupaie.data.database import Database
from edupaie.data.migrator import Migrator
from edupaie.data.repositories import PaymentRepository, ReceiptRepository, StudentRepository
from edupaie.services import DashboardService, PaymentService, ReceiptService, StudentService
from edupaie.ui.error_handler import install_excepthook
from edupaie.ui.main_window import MainWindow
from edupaie.utils.logging_setup import setup_logging

logger = logging.getLogger("edupaie")


def _student_count(db_path) -> int:
    """Compte les élèves dans la table *students* (0 si table absente)."""
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        except sqlite3.OperationalError:
            count = 0
        conn.close()
        return count
    except sqlite3.Error:
        return -1  # base illisible


def ensure_database() -> None:
    """Premier démarrage : copie du jeu de test vers %APPDATA%/EduPaie/.

    Avec --onefile, l'exe vit dans un dossier temporaire : la base doit donc
    toujours être écrite dans le dossier utilisateur (cf. config.data_dir).

    Comportement :
    * Base inexistante  → copie de la seed.
    * Base existante mais vide (0 élève) → sauvegarde + recopie de la seed.
    * Base existante avec des élèves → laisse intacte (données utilisateur).
    """
    if not config.SEED_DB.exists():
        logger.error("Seed introuvable : %s", config.SEED_DB)
        return

    if not config.DB_PATH.exists():
        config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(config.SEED_DB, config.DB_PATH)
        logger.info("Base initialisée depuis la seed : %s", config.DB_PATH)
        return

    count = _student_count(config.DB_PATH)
    if count <= 0:
        backup = config.DB_PATH.with_name(config.DB_PATH.name + ".bak")
        shutil.copy2(config.DB_PATH, backup)
        shutil.copyfile(config.SEED_DB, config.DB_PATH)
        if count < 0:
            logger.warning(
                "Base illisible — sauvegarde → %s, recopie de la seed", backup
            )
        else:
            logger.info("Base vide — sauvegarde → %s, recopie de la seed", backup)
    else:
        logger.info("Base existante : %s (%d élèves)", config.DB_PATH, count)


def run() -> int:
    setup_logging()
    install_excepthook()
    logger.info("Démarrage d'EduPaie (debug=%s, base=%s)", config.DEBUG, config.DB_PATH)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.APP_NAME)

    try:
        ensure_database()

        db = Database(config.DB_PATH)
        applied = Migrator(db, config.MIGRATIONS_DIR).migrate()
        if applied:
            logger.info("Migrations appliquées : %s", ", ".join(applied))

        # Injection de dépendances : les services reçoivent leurs repositories.
        students = StudentRepository(db)
        payments = PaymentRepository(db)
        receipts = ReceiptRepository(db)
        services = {
            "student": StudentService(students, payments),
            "payment": PaymentService(db, students, payments, receipts, caissier=config.CAISSIER),
            "receipt": ReceiptService(receipts),
            "dashboard": DashboardService(students, payments),
        }

        # Log de démarrage : chemin + statistiques de la base
        logger.info(
            "Données chargées : %d élèves, %d paiements, %d reçus",
            students.count(), payments.count(), receipts.count(),
        )

        if config.THEME_PATH.exists():
            app.setStyleSheet(config.THEME_PATH.read_text(encoding="utf-8"))

        window = MainWindow(
            student_service=services["student"],
            payment_service=services["payment"],
            receipt_service=services["receipt"],
            dashboard_service=services["dashboard"],
        )
        window.show()
    except Exception:
        logger.exception("Échec du démarrage")
        QMessageBox.critical(
            None,
            "EduPaie — échec du démarrage",
            "L'application n'a pas pu démarrer.\n"
            "Le détail est disponible dans logs/edupaie.log.",
        )
        return 1

    exit_code = app.exec()
    logger.info("Arrêt d'EduPaie (code %s)", exit_code)
    return exit_code
