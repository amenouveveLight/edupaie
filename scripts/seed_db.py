"""Régénère la base de jeu de test : resources/seed/edupaie_seed.db (livrable).

Usage :  python scripts/seed_db.py

La base créée est versionnée (migrations appliquées) et contient des élèves
et des paiements réalistes pour démontrer l'application dès le 1er lancement.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edupaie import config  # noqa: E402
from edupaie.data.database import Database  # noqa: E402
from edupaie.data.migrator import Migrator  # noqa: E402
from edupaie.data.repositories import (  # noqa: E402
    PaymentRepository,
    ReceiptRepository,
    StudentRepository,
)
from edupaie.services import PaymentService, StudentService  # noqa: E402
from edupaie.utils.formatting import current_school_year  # noqa: E402

TARGET = ROOT / "resources" / "seed" / "edupaie_seed.db"

# (prénom, nom, classe, frais annuels, tuteur, tél.)
STUDENTS = [
    ("Awa", "Diallo", "6ème A", 75000, "M. Diallo Ibrahim", "+225 07 11 22 33"),
    ("Kal", "Koné", "6ème A", 75000, "Mme Koné Aminata", "+225 05 44 55 66"),
    ("Moussa", "Traoré", "6ème A", 75000, "M. Traoré Sékou", "+225 01 77 88 99"),
    ("Fatou", "Bamba", "6ème B", 75000, "Mme Bamba Adjoua", "+225 07 23 45 67"),
    ("Yao", "N'Guessan", "6ème B", 75000, "M. N'Guessan Koffi", "+225 05 34 56 78"),
    ("Aïcha", "Coulibaly", "5ème A", 85000, "Mme Coulibaly Fatou", "+225 01 45 67 89"),
    ("Bakary", "Sanogo", "5ème A", 85000, "M. Sanogo Mamadou", "+225 07 56 78 90"),
    ("Adjoa", "Kouassi", "5ème B", 85000, "Mme Kouassi Akissi", "+225 05 67 89 01"),
    ("Ibrahim", "Cissé", "4ème A", 95000, "M. Cissé Souleymane", "+225 01 78 90 12"),
    ("Nadège", "Ouattara", "4ème A", 95000, "Mme Ouattara Marie", "+225 07 89 01 23"),
    ("Serge", "Yao", "3ème A", 110000, "M. Yao Konan", "+225 05 90 12 34"),
    ("Rachelle", "Assi", "3ème A", 110000, "Mme Assi Bernadette", "+225 01 01 23 45"),
]

# (index élève, fraction réglée 1.0 = soldé, jours en arrière)
PAYMENTS = [
    (0, 0.5, 45), (0, 0.5, 12),
    (1, 1.0, 38),
    (2, 0.4, 30), (2, 0.3, 8),
    (3, 1.0, 52),
    (4, 0.6, 25),
    (5, 0.5, 40), (5, 0.5, 9),
    (6, 0.3, 20),
    (7, 1.0, 60),
    (8, 0.5, 22), (8, 0.5, 6),
    (9, 0.7, 18),
    (10, 0.5, 35), (10, 0.5, 4),
    (11, 0.25, 15),
]

MODES = ["ESPECES", "MOBILE_MONEY", "VIREMENT", "CHEQUE"]


def main() -> int:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists():
        TARGET.unlink()

    db = Database(TARGET)
    applied = Migrator(db, config.MIGRATIONS_DIR).migrate()
    print("Migrations :", ", ".join(applied))

    students_svc = StudentService(StudentRepository(db), PaymentRepository(db))
    payment_svc = PaymentService(
        db, StudentRepository(db), PaymentRepository(db), ReceiptRepository(db)
    )

    created = []
    school_year = current_school_year()
    for first, last, klass, fee, guardian, phone in STUDENTS:
        student = students_svc.create(
            first_name=first, last_name=last, class_name=klass,
            annual_fee=fee, school_year=school_year,
            guardian_phone=f"{guardian} - {phone}",
        )
        created.append(student)
        print(f"  + {student.full_name} ({klass}, {fee} FCFA)")

    today = date.today()
    for position, (index, fraction, days_ago) in enumerate(PAYMENTS):
        student = created[index]
        amount = int(student.annual_fee * fraction)
        paid_on = today - timedelta(days=days_ago)
        _, receipt = payment_svc.register(
            student_id=student.id,
            amount=amount,
            mode=MODES[position % len(MODES)],
            paid_on=paid_on.isoformat(),
            note="",
        )
        print(f"    {receipt.number}  {amount:>7} FCFA  {student.full_name}")

    print(f"\nBase générée : {TARGET} ({TARGET.stat().st_size} octets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
