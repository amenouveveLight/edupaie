"""Configuration globale : chemins (dev vs exe PyInstaller), mode debug, ressources."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "EduPaie"
DEBUG = os.getenv("EDUPAIE_DEBUG", "0") == "1"


def resource_path(relative: str) -> Path:
    """Chemin d'une ressource embarquée (dev ou exe PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / relative


def data_dir() -> Path:
    """Dossier de données utilisateur (persistant, hors exe)."""
    root = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


# Fichiers internes au paquet : résolus à côté du module, donc valables en dev,
# en install (package-data) et dans l'exe (cf. datas dans edupaie.spec).
PACKAGE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = PACKAGE_DIR / "data" / "migrations"
THEME_PATH = PACKAGE_DIR / "ui" / "theme.qss"

# Ressources livrées à la racine du projet / de l'exe.
# Priorité : variable d'environnement EDUPAIE_DB > debug > défaut utilisateur.
_env_db = os.getenv("EDUPAIE_DB")
if _env_db:
    DB_PATH = Path(_env_db)
else:
    DB_PATH = data_dir() / ("edupaie_dev.db" if DEBUG else "edupaie.db")
SEED_DB = resource_path("resources/seed/edupaie_seed.db")
LOG_DIR = data_dir() / "logs"
RECEIPT_DIR = data_dir() / "receipts"
ICONS_DIR = resource_path("resources/icons")

# Année scolaire par défaut (utilisée par le seed et les nouvelles fiches).
DEFAULT_SCHOOL_YEAR = "2026-2027"

# Nom du caissier affiche sur les reçus (variable d'environnement ou defaut).
CAISSIER = os.getenv("EDUPAIE_CAISSIER", "École")
