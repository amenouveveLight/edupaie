import re
from pathlib import Path

ROOT = Path(".").resolve()
SKIP = {"env", ".venv", "build", "dist", "dist2", "Output", "__pycache__", ".git", "sauvegardes"}
out = []

def log(s=""):
    out.append(s)

def keep(p):
    return not (set(p.relative_to(ROOT).parts) & SKIP)

allfiles = [p for p in ROOT.rglob("*") if p.is_file() and keep(p)]
py = [p for p in allfiles if p.suffix == ".py"]

log("== 1. STRUCTURE ==")
log(f"Fichiers: {len(allfiles)} | Python: {len(py)} | SQL: {sum(p.suffix == '.sql' for p in allfiles)}")
for d in sorted({p.relative_to(ROOT).parts[0] for p in allfiles if len(p.relative_to(ROOT).parts) > 1}):
    n = sum(1 for p in allfiles if p.relative_to(ROOT).parts[0] == d)
    log(f"  {d}/  ({n} fichiers)")
for name in ["main.py", "edupaie.spec", "EduPaieSetup.iss", "requirements.txt",
             ".gitignore", "README.md", "ARCHITECTURE.md"]:
    log(f"  {'OK ' if (ROOT / name).exists() else 'MANQUE'} {name}")

log("\n== 2. FICHIERS .db / .bak DANS LE PROJET (donnees sensibles ?) ==")
for p in allfiles:
    if p.suffix in {".db", ".bak"} or p.name.endswith(("-wal", "-shm")):
        log(f"  {p.relative_to(ROOT)}  ({p.stat().st_size} octets)")

FORBID = {
    "domain":   {"data", "services", "ui", "PySide6", "sqlite3"},
    "data":     {"services", "ui", "PySide6"},
    "services": {"ui", "PySide6", "sqlite3"},
    "ui":       {"sqlite3", "data"},
}
imp = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))")
sql = re.compile(r"(SELECT\s.+\sFROM\s|INSERT\s+INTO\s|UPDATE\s+\w+\s+SET\s|DELETE\s+FROM\s)", re.I)

log("\n== 3. REGLE DE DEPENDANCE ui > services > data > domain ==")
viol = 0
for p in py:
    layer = next((x for x in p.relative_to(ROOT).parts if x in FORBID), None)
    if not layer:
        continue
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        m = imp.match(line)
        if m:
            mod = m.group(1) or m.group(2)
            bad = FORBID[layer] & set(mod.split("."))
            if bad:
                viol += 1
                log(f"  [{layer}] {p.relative_to(ROOT)}:{i}  import interdit {sorted(bad)} -> {line.strip()}")
        if layer in {"ui", "services"} and sql.search(line):
            viol += 1
            log(f"  [{layer}] {p.relative_to(ROOT)}:{i}  SQL dans la mauvaise couche")
log(f"  Violations: {viol}")

log("\n== 4. CHEMINS EN DUR / SECRETS ==")
pat = re.compile(r"(C:\\\\?chemin|chemin.vers|[A-Z]:\\\\?Users|password\s*=\s*[\"'][^\"']+[\"']|admin['\"]\s*,\s*['\"]admin)", re.I)
for p in py + [x for x in allfiles if x.suffix in {".spec", ".iss", ".bat", ".ini", ".json", ".toml"}]:
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if pat.search(line):
            log(f"  {p.relative_to(ROOT)}:{i}  {line.strip()[:110]}")

log("\n== 5. TODO / FIXME / except nus ==")
for p in py:
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if re.search(r"TODO|FIXME|XXX|^\s*except\s*:|except Exception:\s*pass", line):
            log(f"  {p.relative_to(ROOT)}:{i}  {line.strip()[:100]}")

log("\n== 6. MIGRATIONS ET TESTS ==")
for p in sorted(allfiles):
    if p.suffix == ".sql" or (p.suffix == ".py" and p.name.startswith("test_")):
        log(f"  {p.relative_to(ROOT)}")

Path("scan_report.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
print("\nRapport enregistre dans scan_report.txt")