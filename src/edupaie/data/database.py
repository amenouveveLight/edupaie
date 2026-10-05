"""Connexion SQLite : PRAGMA, connexion courte, transactions tout-ou-rien."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class Database:
    """Fabrique de connexions. Une connexion = un contexte (thread/transaction)."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = None  # on gère BEGIN/COMMIT nous-mêmes
        conn.execute("PRAGMA foreign_keys = ON")
        if str(self.path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Connexion ouverte puis fermée (lectures hors transaction)."""
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        """Transaction : commit si tout se passe bien, rollback sinon (tout ou rien).

        immediate=True verrouille la base dès le début (écritures concurrentes
        sur le compteur de reçus, par exemple).
        """
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            try:
                yield conn
            except BaseException:
                conn.rollback()
                raise
            else:
                conn.commit()
