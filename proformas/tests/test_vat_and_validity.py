from datetime import datetime
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from proformas.forms import ParameterForm
from proformas.models import Parameter, VatRate
from proformas.services import (
    add_line,
    change_proforma,
    create_draft,
    issue_proforma,
    quote_vat_breakdown,
    update_draft,
    validity_days_value,
)

pytestmark = pytest.mark.django_db


@pytest.mark.unit
def test_create_draft_copies_default_validity_days(staff_user, site):
    proforma = create_draft(site, staff_user)
    assert proforma.validity_days == 7


@pytest.mark.unit
def test_create_draft_uses_parameter_validity_days(staff_user, site):
    Parameter.objects.update_or_create(
        key="default_validity_days", defaults={"value": "14"}
    )
    proforma = create_draft(site, staff_user)
    assert proforma.validity_days == 14


@pytest.mark.unit
def test_update_draft_validity_days(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    update_draft(proforma, staff_user, validity_days=30)
    proforma.refresh_from_db()
    assert proforma.validity_days == 30


@pytest.mark.unit
def test_validity_days_value_rejects_out_of_range():
    with pytest.raises(ValidationError, match="1 and 365"):
        validity_days_value(0)
    with pytest.raises(ValidationError, match="1 and 365"):
        validity_days_value(366)


@pytest.mark.unit
def test_uniform_vat_on_discounted_equipment_tubing_and_labour(
    staff_user, site, indoor, tubing
):
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
    assert proforma.grand_total == Decimal("1035.00")
    assert proforma.vat_amount == Decimal("238.05")
    assert proforma.total_with_vat == Decimal("1273.05")
    indoor_line = proforma.lines.filter(parent_line__isnull=False).get()
    outdoor_line = proforma.lines.filter(parent_line__isnull=True).get()
    assert indoor_line.vat_code == "VAT23"
    assert indoor_line.vat_amount == Decimal("112.70")
    assert outdoor_line.vat_amount == Decimal("113.85")


@pytest.mark.unit
def test_exempt_equipment_still_taxes_labour_at_default(staff_user, site, indoor):
    exempt, _ = VatRate.objects.get_or_create(
        code="VAT_EXEMPT",
        defaults={"label": "Exempt", "rate": Decimal("0.0000"), "is_default": False},
    )
    indoor.vat_rate = exempt
    indoor.save()
    outdoor = indoor.outdoor_matches.filter(is_default=True).get().outdoor
    outdoor.vat_rate = exempt
    outdoor.save()
    proforma = create_draft(
        site, staff_user, discount_percent=0, extra_labour=Decimal("100.00")
    )
    add_line(proforma, indoor, staff_user, quantity=1)
    proforma.refresh_from_db()
    assert proforma.vat_amount == Decimal("23.00")
    assert proforma.total_with_vat == proforma.grand_total + proforma.vat_amount


@pytest.mark.unit
def test_mixed_vat_rates_allocate_equipment_discount(staff_user, site, indoor):
    vat13, _ = VatRate.objects.get_or_create(
        code="VAT13",
        defaults={"label": "13%", "rate": Decimal("0.1300"), "is_default": False},
    )
    outdoor = indoor.outdoor_matches.filter(is_default=True).get().outdoor
    outdoor.vat_rate = vat13
    outdoor.save()
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    proforma.refresh_from_db()
    indoor_line = proforma.lines.filter(item=indoor).get()
    outdoor_line = proforma.lines.filter(item=outdoor).get()
    assert indoor_line.vat_rate == Decimal("0.2300")
    assert outdoor_line.vat_rate == Decimal("0.1300")
    assert indoor_line.vat_amount == Decimal("103.50")
    assert outdoor_line.vat_amount == Decimal("64.35")
    assert proforma.vat_amount == Decimal("167.85")
    assert proforma.total_with_vat == proforma.grand_total + proforma.vat_amount


@pytest.mark.unit
def test_issue_freezes_vat_when_catalog_rate_changes(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=0)
    add_line(proforma, indoor, staff_user, quantity=1)
    issued = issue_proforma(proforma, staff_user)
    frozen = issued.vat_amount
    vat = indoor.vat_rate
    vat.rate = Decimal("0.0600")
    vat.save()
    issued.refresh_from_db()
    assert issued.vat_amount == frozen
    indoor_line = issued.lines.filter(item=indoor).get()
    assert indoor_line.vat_rate == Decimal("0.2300")
    assert indoor_line.vat_code == "VAT23"


@pytest.mark.unit
def test_issue_sets_valid_until_from_lisbon_calendar_date(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, validity_days=7)
    add_line(proforma, indoor, staff_user, quantity=1)
    frozen = datetime(2026, 9, 9, 23, 30, tzinfo=ZoneInfo("Europe/Lisbon"))
    with patch("proformas.services.timezone.now", return_value=frozen):
        issued = issue_proforma(proforma, staff_user)
    assert issued.issued_at == frozen
    assert issued.valid_until.isoformat() == "2026-09-16"


@pytest.mark.unit
def test_changing_parameter_does_not_rewrite_issued_validity(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, validity_days=7)
    add_line(proforma, indoor, staff_user, quantity=1)
    issued = issue_proforma(proforma, staff_user)
    until = issued.valid_until
    Parameter.objects.update_or_create(
        key="default_validity_days", defaults={"value": "30"}
    )
    issued.refresh_from_db()
    assert issued.validity_days == 7
    assert issued.valid_until == until


@pytest.mark.unit
def test_change_copies_validity_days_not_issued_dates(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, validity_days=21)
    add_line(proforma, indoor, staff_user, quantity=1)
    issued = issue_proforma(proforma, staff_user)
    new = change_proforma(issued, staff_user)
    assert new.validity_days == 21
    assert new.issued_at is None
    assert new.valid_until is None


@pytest.mark.unit
def test_parameter_form_rejects_invalid_validity_days():
    parameter, _ = Parameter.objects.get_or_create(
        key="default_validity_days", defaults={"value": "7"}
    )
    form = ParameterForm({"value": "0"}, instance=parameter)
    assert not form.is_valid()
    assert "value" in form.errors


@pytest.mark.unit
@pytest.mark.django_db
def test_quote_vat_breakdown_groups_lines_and_extra_labour(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10, extra_labour=100)
    add_line(proforma, indoor, staff_user, quantity=1)
    issued = issue_proforma(proforma, staff_user)
    rows = quote_vat_breakdown(issued)
    assert rows
    assert sum(row["vat_amount"] for row in rows) == issued.vat_amount
    assert any(row["rate_percent"] == Decimal("23.00") for row in rows)


@pytest.mark.integration
@pytest.mark.django_db
def test_quote_html_shows_vat_and_validity(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user, validity_days=7)
    add_line(proforma, indoor, staff_user, quantity=1)
    issued = issue_proforma(proforma, staff_user)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[issued.pk])).content.decode()
    assert "VAT" in body
    assert "Tax base" in body
    assert "Total of document" in body
    assert "Valid until" in body
    assert str(issued.valid_until) in body
    assert str(issued.total_with_vat) in body


@pytest.mark.integration
def test_cli_validity_days(staff_user, site, indoor):
    out = StringIO()
    call_command(
        "create_proforma",
        "--user",
        staff_user.email,
        "--site",
        str(site.pk),
        "--line",
        f"{indoor.pk}:1",
        "--validity-days",
        "21",
        stdout=out,
    )
    from proformas.models import Proforma

    proforma = Proforma.objects.get(number=out.getvalue().strip())
    assert proforma.validity_days == 21
