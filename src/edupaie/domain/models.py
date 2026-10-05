"""Modèles de données purs (dataclasses, pas d'ORM, pas de Qt)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from edupaie.domain.enums import PaymentMode


@dataclass
class Student:
    """Élève. Les montants sont des entiers en FCFA (jamais de float)."""

    first_name: str
    last_name: str
    class_name: str
    school_year: str = ""  # ex. 2026-2027
    annual_fee: int = 0
    guardian_phone: str = ""
    email: str = ""
    id: int | None = None
    created_at: str = ""
    updated_at: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.last_name.upper()} {self.first_name}"

    def with_id(self, row_id: int) -> Student:
        return replace(self, id=row_id)


@dataclass
class Payment:
    """Paiement enregistré (montant entier en FCFA)."""

    student_id: int
    amount: int
    mode: PaymentMode
    paid_on: str  # ISO AAAA-MM-JJ
    note: str = ""
    id: int | None = None
    created_at: str = ""


@dataclass
class Receipt:
    """Reçu = instantané figé au moment de l'émission.

    Tous les champs sont copiés ici (nom, classe, solde après paiement...) pour
    qu'une réimpression soit strictement identique, même si l'élève change ensuite.
    """

    number: str
    payment_id: int
    student_id: int
    student_name: str
    class_name: str
    amount: int
    mode: PaymentMode
    paid_on: str
    balance_after: int
    total_paid_after: int
    caissier: str = ""
    note: str = ""
    id: int | None = None
    issued_at: str = ""



@dataclass
class ReceiptDraft:
    """Reçu provisoire : snapshot identique à ``Receipt`` mais sans numéro définitif.

    Produit par ``PaymentService.preview()`` pour montrer l'aperçu AVANT validation.
    Aucune écriture n'a lieu : ``number`` est un texte d'attente et le compteur de
    reçus n'est jamais incrémenté pour un aperçu. Le rendu PDF accepte un ``Receipt``
    ou un ``ReceiptDraft`` de manière identique (filigrane pour le brouillon).
    """

    student_name: str
    class_name: str
    amount: int
    mode: PaymentMode
    paid_on: str  # ISO AAAA-MM-JJ
    note: str = ""
    total_paid_after: int = 0
    balance_after: int = 0
    caissier: str = ""
    number: str = "Attribué à la validation"
    student_id: int = 0
    issued_at: str = ""


@dataclass
class StudentAccount:
    """Élève + total réglé, base du calcul du solde et du statut."""

    student: Student
    total_paid: int = 0
    payments: list[Payment] = field(default_factory=list)
