"""Formatage monétaire et dates à la française."""

from datetime import date, datetime

# On formate en ASCII pur : les chaînes passent dans un PDF aux polices Helvetica
# (latin-1), qui ne supportent ni espaces insécables ni typographie avancée.


def format_fcfa(amount: int) -> str:
    """1250000 -> '1 250 000 FCFA'."""
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(amount):,}".replace(",", " ") + " FCFA"


def parse_date(value: str | date | datetime) -> date:
    """Accepte 'YYYY-MM-DD', 'DD/MM/YYYY', date ou datetime."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date invalide : {value!r} (attendu JJ/MM/AAAA ou AAAA-MM-JJ)")


def format_date(value: str | date | datetime) -> str:
    """'2026-10-01' -> '01/10/2026'."""
    return parse_date(value).strftime("%d/%m/%Y")


def format_date_long(value: str | date | datetime) -> str:
    """'2026-10-01' -> '01 octobre 2026'."""
    months = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    )
    d = parse_date(value)
    return f"{d.day:02d} {months[d.month - 1]} {d.year}"


def current_school_year(today: date | None = None) -> str:
    """Année scolaire en cours : démarre en septembre.

    2026-08-15 -> "2025-2026" ; 2026-10-01 -> "2026-2027".
    """
    today = today or date.today()
    start = today.year if today.month >= 9 else today.year - 1
    return f"{start}-{start + 1}"


def latin1_safe(text: str) -> str:
    """Remplace les caractères hors latin-1 pour les polices PDF standard."""
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", "€": "EUR",
        " ": " ", " ": " ", "−": "-",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")
