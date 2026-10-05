"""Repositories : SQL concentré ici, aucune règle métier."""

from edupaie.data.repositories.payment_repository import PaymentRepository
from edupaie.data.repositories.receipt_repository import ReceiptRepository
from edupaie.data.repositories.student_repository import StudentRepository

__all__ = ["PaymentRepository", "ReceiptRepository", "StudentRepository"]
