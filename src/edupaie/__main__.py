"""Point d'entrée : permet d'exécuter l'application avec ``python -m edupaie``."""

import sys

from edupaie.app import run

if __name__ == "__main__":
    sys.exit(run())
