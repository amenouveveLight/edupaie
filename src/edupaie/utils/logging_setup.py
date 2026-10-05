"""Journalisation : fichier rotatif dans %APPDATA%/EduPaie/logs."""

import logging
from logging.handlers import RotatingFileHandler

from edupaie import config


def setup_logging() -> logging.Logger:
    """Configure le logger racine 'edupaie' (console en debug, fichier rotatif)."""
    logger = logging.getLogger("edupaie")
    if logger.handlers:  # déjà configuré (tests, double appel)
        return logger

    logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        config.LOG_DIR / "edupaie.log",
        maxBytes=500_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    if config.DEBUG:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)

    logger.debug("Journal initialisé dans %s", config.LOG_DIR)
    return logger
