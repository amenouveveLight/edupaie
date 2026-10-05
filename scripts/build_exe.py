"""Wrapper Python du build PyInstaller (équivalent de build.bat).

Usage :  python scripts/build_exe.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(ROOT / "edupaie.spec"),
    ]
    print(" ".join(command))
    code = subprocess.call(command, cwd=ROOT)
    if code == 0:
        print(f"\nExecutable : {ROOT / 'dist' / 'EduPaie.exe'}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
