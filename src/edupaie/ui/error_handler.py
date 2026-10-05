"""Gestionnaire global d'erreurs : plus aucun crash silencieux.

Toute exception non catchée est journalisée puis affichée dans une boîte
dialogue au lieu de tuer l'application.
"""

import logging
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

logger = logging.getLogger("edupaie.ui")


def install_excepthook() -> None:
    """Remplace sys.excepthook : log fichier + QMessageBox, jamais de crash blanc."""

    def hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        logger.critical(
            "Exception non gérée", exc_info=(exc_type, exc_value, exc_tb)
        )
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))[-2000:]
        try:
            app = QApplication.instance()
            if app is not None:
                QMessageBox.critical(
                    None,
                    "Erreur inattendue",
                    f"Une erreur inattendue s'est produite.\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"Le détail a été enregistré dans le journal (logs/edupaie.log).",
                )
        except Exception:  # si même la boîte échoue, on garde au moins le log
            logger.exception("Impossible d'afficher la boîte d'erreur")
        del detail

    sys.excepthook = hook
