"""Service paiements : la transaction « tout ou rien » du projet.

register() enchaîne : valider → vérifier le solde → insérer le paiement →
numéroter et créer le reçu → commit. La moindre erreur annule tout, compteur
de reçus compris.

preview() calcule le même snapshot en lecture seule (aucune écriture, le
compteur de reçus n'est pas consommé) afin de montrer l'aperçu du reçu
avant validation effective.
"""

from datetime import datetime

from edupaie.data.database import Database
from edupaie.data.repositories.payment_repository import PaymentRepository
from edupaie.data.repositories.receipt_repository import ReceiptRepository
from edupaie.data.repositories.student_repository import StudentRepository
from edupaie.domain.exceptions import NotFoundError, OverpaymentError
from edupaie.domain.models import Payment, Receipt, ReceiptDraft
from edupaie.services import balance, validators
from edupaie.utils.formatting import format_fcfa

# Texte d'attente affiché dans un brouillon, jamais un vrai numéro REC.
PREVIEW_NUMBER = "Attribué à la validation"


class PaymentService:
    def __init__(
        self,
        db: Database,
        students: StudentRepository,
        payments: PaymentRepository,
        receipts: ReceiptRepository,
        caissier: str = "École",
    ):
        self.db = db
        self.students = students
        self.payments = payments
        self.receipts = receipts
        self.caissier = caissier

    # --- préparation partagée -----------------------------------------

    @staticmethod
    def _validated(amount, mode, paid_on, note) -> tuple:
        """Valide les entrées comme register() et preview() (aucun doublon)."""
        amount = validators.validate_amount(amount)
        mode = validators.validate_mode(mode)
        paid_on = validators.validate_date(paid_on).isoformat()
        note = str(note or "").strip()
        return amount, mode, paid_on, note

    def _snapshot(self, student_id, amount, mode, paid_on, conn) -> dict:
        """Calcule le snapshot du reçu en lecture seule.

        Règles identiques selon que l'appel provient de preview() (lecture) ou
        de register() (transaction) : validation, refus de surpaiement par
        ``OverpaymentError``. Aucune écriture n'a lieu ici.
        """
        student = self.students.get_conn(conn, student_id)
        if student is None:
            raise NotFoundError(f"Élève introuvable (id {student_id}).")

        paid_before = self.payments.total_for_student(student_id, conn=conn)
        solde_before = balance.balance_of(student.annual_fee, paid_before)
        if amount > solde_before:
            raise OverpaymentError(
                f"Surpaiement refusé : le solde restant est de "
                f"{format_fcfa(max(solde_before, 0))} pour {student.full_name}."
            )
        total_after = paid_before + amount
        return {
            "student": student,
            "amount": amount,
            "mode": mode,
            "paid_on": paid_on,
            "total_paid_after": total_after,
            "balance_after": balance.balance_of(student.annual_fee, total_after),
        }

    # --- aperçu (lecture seule, zéro écriture) ------------------------

    def preview(self, student_id, amount, mode, paid_on, note: str = "") -> ReceiptDraft:
        """Calcule un aperçu de reçu sans rien écrire en base.

        Le compteur de reçus n'est jamais incrémenté pour un aperçu : le
        numéro affiché est un texte d'attente (``PREVIEW_NUMBER``). Les
        valeurs (``total_paid_after``, ``balance_after``) sont strictement
        identiques à celles du reçu que ``register()`` émettra avec les mêmes
        entrées, tant que la base n'a pas changé entre-temps.
        """
        amount, mode, paid_on, note = self._validated(amount, mode, paid_on, note)
        with self.db.connection() as conn:  # lecture seule : pas de transaction d'écriture
            snap = self._snapshot(student_id, amount, mode, paid_on, conn)
        student = snap["student"]
        return ReceiptDraft(
            student_id=student.id or 0,
            student_name=student.full_name,
            class_name=student.class_name,
            amount=snap["amount"],
            mode=snap["mode"],
            paid_on=snap["paid_on"],
            note=note,
            total_paid_after=snap["total_paid_after"],
            balance_after=snap["balance_after"],
            caissier=self.caissier,
            issued_at=datetime.now().isoformat(timespec="seconds"),
        )

    # --- enregistrement (transaction tout ou rien) --------------------

    def register(
        self, student_id, amount, mode, paid_on, note: str = ""
    ) -> tuple[Payment, Receipt]:
        """Enregistre un paiement et émet son reçu, en une seule transaction.

        Règle du sujet : le solde ne doit JAMAIS passer sous 0 — tout
        montant supérieur au solde restant est refusé (OverpaymentError).
        La validation est refaite dans la transaction : si le solde a changé
        entre l'aperçu et la confirmation, le refus ou le rollback annule tout.
        """
        amount, mode, paid_on, note = self._validated(amount, mode, paid_on, note)
        with self.db.transaction(immediate=True) as conn:
            snap = self._snapshot(student_id, amount, mode, paid_on, conn)
            now = datetime.now().isoformat(timespec="seconds")
            student = snap["student"]

            payment = Payment(
                student_id=student.id,
                amount=snap["amount"],
                mode=snap["mode"],
                paid_on=snap["paid_on"],
                note=note,
                created_at=now,
            )
            payment.id = self.payments.insert(conn, payment)

            # Compteur incrémenté DANS la transaction : rollback => numéro jamais consommé.
            number = self.receipts.next_number(conn, datetime.now().year)
            receipt = Receipt(
                number=number,
                payment_id=payment.id,
                student_id=student.id,
                student_name=student.full_name,
                class_name=student.class_name,
                amount=snap["amount"],
                mode=snap["mode"],
                paid_on=snap["paid_on"],
                balance_after=snap["balance_after"],
                total_paid_after=snap["total_paid_after"],
                caissier=self.caissier,
                note=note,
                issued_at=now,
            )
            receipt.id = self.receipts.insert(conn, receipt)

        return payment, receipt
