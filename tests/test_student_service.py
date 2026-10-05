"""StudentService : validations, suppression protégée, filtre par statut."""

import pytest

from edupaie.domain.enums import PaymentStatus
from edupaie.domain.exceptions import NotFoundError, ValidationError
from edupaie.utils.formatting import current_school_year


def test_create_cleans_and_stores_data(student_service):
    student = student_service.create(
        "  Awa ", " Diallo ", " 6ème A ", annual_fee="50000",
        school_year="2026-2027", guardian_phone="+225 07 00 00 00",
    )
    assert student.first_name == "Awa"
    assert student.last_name == "Diallo"
    assert student.class_name == "6ème A"
    assert student.school_year == "2026-2027"
    assert student.annual_fee == 50000
    assert student.id is not None
    assert student.created_at


def test_create_defaults_to_current_school_year(student_service):
    student = student_service.create("X", "Y", "6ème A", 0)
    assert student.school_year == current_school_year()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"first_name": "", "last_name": "X", "class_name": "6ème A", "annual_fee": 0},
        {"first_name": "X", "last_name": "  ", "class_name": "6ème A", "annual_fee": 0},
        {"first_name": "X", "last_name": "Y", "class_name": "", "annual_fee": 0},
        {"first_name": "X", "last_name": "Y", "class_name": "6ème A", "annual_fee": -1},
        {"first_name": "X", "last_name": "Y", "class_name": "6ème A", "annual_fee": "libre"},
        {"first_name": "X", "last_name": "Y", "class_name": "6ème A", "annual_fee": 0,
         "school_year": "2026"},
        {"first_name": "X", "last_name": "Y", "class_name": "6ème A", "annual_fee": 0,
         "school_year": "2026-2028"},
    ],
)
def test_create_rejects_invalid_data(student_service, kwargs):
    with pytest.raises(ValidationError):
        student_service.create(**kwargs)


def test_update_unknown_student_raises(student_service):
    from edupaie.domain.models import Student

    ghost = Student(first_name="A", last_name="B", class_name="C", id=999)
    with pytest.raises(NotFoundError):
        student_service.update(ghost)


def test_delete_blocked_when_payments_exist(student_service, payment_service, make_student):
    student = make_student(annual_fee=50000)
    payment_service.register(student.id, 10000, "ESPECES", "2026-10-01")

    with pytest.raises(ValidationError):
        student_service.delete(student.id)
    assert student_service.get(student.id) is not None  # toujours là


def test_delete_allowed_without_payments(student_service, make_student):
    student = make_student()
    student_service.delete(student.id)
    with pytest.raises(NotFoundError):
        student_service.get(student.id)


def test_delete_unknown_raises(student_service):
    with pytest.raises(NotFoundError):
        student_service.delete(4242)


def test_list_filters_by_status(student_service, payment_service, make_student):
    soldé = make_student("Soldé", "Elève", annual_fee=10000)
    payment_service.register(soldé.id, 10000, "ESPECES", "2026-10-01")

    partiel = make_student("Partiel", "Elève", annual_fee=10000)
    payment_service.register(partiel.id, 4000, "ESPECES", "2026-10-01")

    make_student("Impaye", "Elève", annual_fee=10000)

    assert len(student_service.list(status="SOLDE")) == 1
    assert len(student_service.list(status="PARTIEL")) == 1
    assert len(student_service.list(status="NON_PAYE")) == 1
    assert student_service.list(status=PaymentStatus.PARTIEL)[0].student.first_name == "Partiel"


def test_dashboard_stats_aggregate(
    student_service, payment_service, make_student, dashboard_service
):
    a = make_student("Awa", "Diallo", "6ème A", annual_fee=50000)
    payment_service.register(a.id, 50000, "ESPECES", "2026-10-01")
    b = make_student("Kal", "Koné", "6ème A", annual_fee=60000)
    payment_service.register(b.id, 20000, "ESPECES", "2026-10-01")
    make_student("Moussa", "Traoré", "5ème B", annual_fee=40000)

    stats = dashboard_service.stats()
    assert stats.total_students == 3
    assert stats.total_collected == 70000
    assert stats.outstanding == 80000  # 0 + 40000 + 40000
    assert stats.count_solde == 1
    assert stats.count_partiel == 1
    assert stats.count_non_paye == 1
    assert stats.recent_payments and len(stats.recent_payments) == 2
    assert {c.class_name for c in stats.per_class} == {"6ème A", "5ème B"}
    assert 0.0 <= stats.collection_rate <= 1.0
