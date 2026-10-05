import sqlite3, os

d = os.path.expandvars(r"%APPDATA%\EduPaie")
for f in ["edupaie.db", "edupaie.db.bak", "edupaie_dev.db"]:
    p = os.path.join(d, f)
    c = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    try:
        def n(t):
            return c.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
        v = c.execute("PRAGMA user_version").fetchone()[0]
        print(f, "| user_version =", v,
              "| eleves =", n("students"),
              "| paiements =", n("payments"),
              "| recus =", n("receipts"))
    except Exception as e:
        print(f, "-> erreur :", e)