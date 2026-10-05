"""Énumérations métier."""

from enum import Enum


class PaymentMode(str, Enum):
    """Mode de règlement accepté par l'école."""

    ESPECES = "ESPECES"
    MOBILE_MONEY = "MOBILE_MONEY"
    VIREMENT = "VIREMENT"
    CHEQUE = "CHEQUE"

    @property
    def label(self) -> str:
        return {
            "ESPECES": "Espèces",
            "MOBILE_MONEY": "Mobile Money",
            "VIREMENT": "Virement",
            "CHEQUE": "Chèque",
        }[self.value]


class PaymentStatus(str, Enum):
    """Statut dérivé du solde : jamais stocké, toujours recalculé."""

    SOLDE = "SOLDE"
    PARTIEL = "PARTIEL"
    NON_PAYE = "NON_PAYE"

    @property
    def label(self) -> str:
        return {
            "SOLDE": "Soldé",
            "PARTIEL": "Partiel",
            "NON_PAYE": "Non payé",
        }[self.value]
