"""Service reçus : lecture des snapshots pour réimpression et historique."""

from edupaie.data.repositories.receipt_repository import ReceiptRepository
from edupaie.domain.exceptions import NotFoundError
from edupaie.domain.models import Receipt


class ReceiptService:
    def __init__(self, receipts: ReceiptRepository):
        self.receipts = receipts

    def get(self, receipt_id: int) -> Receipt:
        receipt = self.receipts.get(receipt_id)
        if receipt is None:
            raise NotFoundError(f"Reçu introuvable (id {receipt_id}).")
        return receipt

    def get_by_number(self, number: str) -> Receipt:
        receipt = self.receipts.get_by_number(number)
        if receipt is None:
            raise NotFoundError(f"Reçu introuvable ({number}).")
        return receipt

    def list_for_student(self, student_id: int) -> list[Receipt]:
        """Historique d'un élève, du plus récent au plus ancien."""
        return self.receipts.list_for_student(student_id)

    def find_for_payment(self, payment_id: int) -> Receipt | None:
        """Reçu émis pour un paiement (None si le paiement n'en a pas)."""
        return self.receipts.get_by_payment_id(payment_id)
