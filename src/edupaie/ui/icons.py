"""Chargement des icônes SVG de resources/icons (gracieux si fichier absent)."""

from PySide6.QtGui import QIcon

from edupaie import config


def icon(name: str) -> QIcon:
    path = config.ICONS_DIR / name
    if path.exists():
        return QIcon(str(path))
    return QIcon()  # icône vide plutôt qu'un plantage
