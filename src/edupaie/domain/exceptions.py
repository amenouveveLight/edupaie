"""Exceptions métier. La couche UI les attrape pour afficher un message propre."""


class EduPaieError(Exception):
    """Base de toutes les erreurs métier."""


class ValidationError(EduPaieError):
    """Données d'entrée invalides (champ vide, montant nul, date incorrecte...)."""


class OverpaymentError(ValidationError):
    """Le paiement ferait un solde négatif (surpaiement non autorisé)."""


class NotFoundError(EduPaieError):
    """Ressource introuvable (élève, paiement, reçu)."""
