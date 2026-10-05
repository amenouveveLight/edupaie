"""Régression : les appels QMessageBox.* ne doivent jamais recevoir ``parent=``
en mot-clé, PySide6 le traite comme positional-only et lève AttributeError.

Le premier argument positionnel est déjà le parent.
"""

from __future__ import annotations

import ast
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[1] / "src" / "edupaie" / "ui"

QMESSAGEBOX_ATTRS = {"warning", "information", "critical", "question", "about"}


def _qmbb_calls(node: ast.AST) -> list[ast.Call]:
    """Renvoie les appels QMessageBox.* présents dans l'arbre."""
    calls = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            name = sub.func.attr
            # QMessageBox.warning(...) ou mbox.warning(...) (import * ou alias)
            if name in QMESSAGEBOX_ATTRS:
                calls.append(sub)
    return calls


def _all_py_files() -> list[Path]:
    files = []
    for p in UI_DIR.rglob("*.py"):
        files.append(p)
    return sorted(files)


def test_no_qmessagebox_call_uses_parent_keyword() -> None:
    offenders: list[str] = []
    for path in _all_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _qmbb_calls(tree):
            for kw in call.keywords:
                if kw.arg == "parent":
                    loc = f"{path}:{call.lineno}"
                    offenders.append(
                        f"{loc} → QMessageBox.{call.func.attr}(..., parent=...)"
                    )
    msg = "parent= est invalide sur QMessageBox.\n" + "\n".join(offenders)
    assert not offenders, msg
