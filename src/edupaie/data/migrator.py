"""Migrations SQL versionnées via PRAGMA user_version.

Chaque fichier `NNN_description.sql` est appliqué une seule fois, dans l'ordre,
dans une transaction : si échec, la version n'avance pas.
"""

import re
import sqlite3
from pathlib import Path

from edupaie.data.database import Database

MIGRATION_RE = re.compile(r"^(\d{3})_[\w-]+\.sql$")


class Migrator:
    def __init__(self, db: Database, migrations_dir: str | Path):
        self.db = db
        self.migrations_dir = Path(migrations_dir)

    def _collect(self) -> list[tuple[int, Path]]:
        """Fichiers de migration triés par version, nom incorrect => ValueError."""
        found: list[tuple[int, Path]] = []
        for path in sorted(self.migrations_dir.glob("*.sql")):
            match = MIGRATION_RE.match(path.name)
            if not match:
                raise ValueError(f"Nom de migration invalide : {path.name} (attendu NNN_nom.sql)")
            found.append((int(match.group(1)), path))
        return sorted(found)

    def current_version(self) -> int:
        with self.db.connection() as conn:
            return conn.execute("PRAGMA user_version").fetchone()[0]

    def pending(self) -> list[Path]:
        current = self.current_version()
        return [path for version, path in self._collect() if version > current]

    def migrate(self) -> list[str]:
        """Applique les migrations en attente. Retourne les noms appliqués."""
        applied: list[str] = []
        for version, path in self._collect():
            current = self.current_version()
            if version <= current:
                continue
            sql = path.read_text(encoding="utf-8")
            # executescript annule toute transaction en cours : on l'encadre nous-mêmes.
            script = f"BEGIN;\n{sql}\nPRAGMA user_version = {version};\nCOMMIT;"
            with self.db.connection() as conn:
                try:
                    conn.executescript(script)
                except sqlite3.Error:
                    conn.execute("ROLLBACK")
                    raise
            applied.append(path.name)
        return applied
