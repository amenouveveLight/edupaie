"""Point d'entrée EduPaie : lance l'application.

Usage ::
    python main.py               # base par défaut (%APPDATA%/EduPaie/edupaie.db)
    python main.py --db /path/x.db
    EDUPAIE_DB=/path/x.db python main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="EduPaie — gestion des paiements scolaires",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Chemin vers la base SQLite (défaut : %APPDATA%/EduPaie/edupaie.db).",
    )
    args = parser.parse_args()

    # Bootstrap du path src/ si le package n'est pas installé.
    try:
        import edupaie  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

    from edupaie import config
    from edupaie.app import run

    if args.db:
        config.DB_PATH = args.db

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
