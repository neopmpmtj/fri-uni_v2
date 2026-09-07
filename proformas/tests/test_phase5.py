from decimal import Decimal

import pytest
from django.utils import timezone

from proformas.models import TubingLength
from proformas.services import add_line, create_draft

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_first_draft_number_of_year(staff_user, site):
    year = timezone.now().year
    proforma = create_draft(site, staff_user)
    assert proforma.number == f"PF-{year}-0001"


def test_line_tubing_formula(staff_user, site, indoor, tubing):
    proforma = create_draft(site, staff_user, discount_percent=0)
    line = add_line(
        proforma,
        indoor,
        staff_user,
        quantity=2,
        extra_tubing=True,
        tubing_length=tubing,
    )
    # 2 × (500 + 40) = 1080
    assert line.line_total == Decimal("1080.00")
    proforma.refresh_from_db()
    assert proforma.tubing_total == Decimal("80.00")
    assert proforma.extra_tubing_metres == Decimal("10.00")
    assert proforma.equipment_subtotal == Decimal("1000.00")


def test_discount_ignores_tubing_and_labour(staff_user, site, indoor, tubing):
    proforma = create_draft(
        site, staff_user, discount_percent=10, extra_labour=Decimal("50.00")
    )
    add_line(
        proforma,
        indoor,
        staff_user,
        quantity=1,
        extra_tubing=True,
        tubing_length=tubing,
    )
    proforma.refresh_from_db()
    # equipment 500, discount 50, tubing 40, labour 50 -> 540
    assert proforma.discount_amount == Decimal("50.00")
    assert proforma.grand_total == Decimal("540.00")


def test_extra_tubing_metres_sums_quantity_times_length(staff_user, site, indoor, tubing):
    short = TubingLength.objects.create(length=Decimal("3.00"), price=Decimal("25.00"))
    proforma = create_draft(site, staff_user, discount_percent=0)
    add_line(
        proforma,
        indoor,
        staff_user,
        quantity=2,
        extra_tubing=True,
        tubing_length=short,
    )
    add_line(
        proforma,
        indoor,
        staff_user,
        quantity=1,
        extra_tubing=True,
        tubing_length=tubing,
    )
    proforma.refresh_from_db()
    assert proforma.extra_tubing_metres == Decimal("11.00")
    assert proforma.tubing_total == Decimal("90.00")
