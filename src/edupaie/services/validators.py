"""Règles de validation des données d'entrée. Aucune dépendance Qt ni SQL."""

import re
from datetime import date

from edupaie.domain.enums import PaymentMode
from edupaie.domain.exceptions import ValidationError
from edupaie.utils.formatting import current_school_year, parse_date

SCHOOL_YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")


def require_text(value, field: str) -> str:
    """Champ obligatoire : non vide après nettoyage."""
    if value is None:
        raise ValidationError(f"Le champ « {field} » est obligatoire.")
    text = str(value).strip()
    if not text:
        raise ValidationError(f"Le champ « {field} » est obligatoire.")
    return text


def validate_fee(value, field: str = "Frais scolaires") -> int:
    """Montant dû : entier >= 0 (les floats sont acceptés s'ils sont entiers)."""
    if isinstance(value, bool) or value is None or value == "":
        raise ValidationError(f"Le champ « {field} » est obligatoire.")
    try:
        fee = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Le champ « {field} » doit être un nombre entier.") from None
    if isinstance(value, float) and value != int(value):
        raise ValidationError(f"Le champ « {field} » doit être un nombre entier (pas de centimes).")
    if fee < 0:
        raise ValidationError(f"Le champ « {field} » ne peut pas être négatif.")
    return fee


def validate_amount(value) -> int:
    """Montant payé : entier strictement positif, en FCFA."""
    if isinstance(value, bool) or value is None or value == "":
        raise ValidationError("Le montant est obligatoire.")
    try:
        amount = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Le montant doit être un nombre entier.") from None
    if isinstance(value, float) and value != int(value):
        raise ValidationError("Le montant doit être un nombre entier (pas de centimes).")
    if amount <= 0:
        raise ValidationError("Le montant doit être strictement supérieur à 0.")
    return amount


def validate_date(value, field: str = "Date") -> date:
    """Date au format AAAA-MM-JJ ou JJ/MM/AAAA, pas dans le futur lointain."""
    try:
        return parse_date(value)
    except ValueError:
        raise ValidationError(
            f"Le champ « {field} » doit être une date valide (JJ/MM/AAAA)."
        ) from None


def validate_school_year(value) -> str:
    """Année scolaire au format AAAA-AAAA consécutives ; None => année courante."""
    if value is None:
        return current_school_year()
    text = str(value).strip()
    match = SCHOOL_YEAR_RE.match(text)
    if not match:
        raise ValidationError("L'année scolaire doit être au format 2026-2027.")
    start, end = int(match.group(1)), int(match.group(2))
    if end != start + 1:
        raise ValidationError("Année scolaire invalide : 2026-2027 et non 2026-2028.")
    return text


def validate_mode(value) -> PaymentMode:
    if isinstance(value, PaymentMode):
        return value
    try:
        return PaymentMode(str(value).strip().upper())
    except ValueError:
        labels = ", ".join(m.label for m in PaymentMode)
        raise ValidationError(f"Mode de paiement invalide. Choisissez : {labels}.") from None


def validate_student(
    first_name, last_name, class_name, annual_fee,
    school_year=None, guardian_phone="", email="",
) -> dict:
    """Valide la fiche élève et retourne les données nettoyées."""
    return {
        "first_name": require_text(first_name, "Prénom"),
        "last_name": require_text(last_name, "Nom"),
        "class_name": require_text(class_name, "Classe"),
        "school_year": validate_school_year(school_year),
        "annual_fee": validate_fee(annual_fee),
        "guardian_phone": str(guardian_phone or "").strip(),
        "email": str(email or "").strip(),
    }
