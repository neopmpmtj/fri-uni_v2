from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from proformas.models import ActivityLog, Proforma
from proformas.services import (
    accept_proforma,
    add_line,
    create_draft,
    issue_proforma,
    reject_proforma,
    unaccept_proforma,
    unreject_proforma,
    update_draft,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def issued(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_issue_freezes_extra_tubing_metres_after_catalog_change(
    staff_user, site, indoor, tubing
):
    proforma = create_draft(site, staff_user, discount_percent=0)
    add_line(
        proforma,
        indoor,
        staff_user,
        quantity=2,
        extra_tubing=True,
        tubing_length=tubing,
    )
    issued = issue_proforma(proforma, staff_user)
    assert issued.extra_tubing_metres == Decimal("10.00")
    tubing.length = Decimal("99.00")
    tubing.save()
    issued.refresh_from_db()
    assert issued.extra_tubing_metres == Decimal("10.00")
    assert issued.lines.first().tubing_length_value == Decimal("5.00")


def test_issue_freezes_line_price_after_catalog_change(issued, indoor):
    frozen_price = issued.lines.first().unit_price
    frozen_total = issued.grand_total
    indoor.list_price = Decimal("999.00")
    indoor.save()
    issued.refresh_from_db()
    assert issued.lines.first().unit_price == frozen_price
    assert issued.grand_total == frozen_total
    assert frozen_price == Decimal("500.00")


def test_issue_snapshots_catalog_names(issued, indoor):
    line = issued.lines.first()
    assert line.family_name == "Air conditioners"
    assert line.sub_family_name == "Split"
    assert line.brand_name == "Mitsu"
    assert line.internal_code == indoor.internal_code
    assert line.power_value == 9000
    assert line.power_unit == "BTU"


def test_issue_snapshots_power_after_catalog_change(issued, indoor):
    line = issued.lines.first()
    indoor.power.unit = "BTU-changed"
    indoor.power.save()
    issued.refresh_from_db()
    line.refresh_from_db()
    assert line.power_value == 9000
    assert line.power_unit == "BTU"


def test_issue_snapshots_client_name(issued, site):
    original = issued.client_name
    site.client.name = "Renamed Ltd"
    site.client.save()
    issued.refresh_from_db()
    assert issued.client_name == original
    assert original == "Acme"


def test_issued_money_update_rejected(issued, staff_user):
    with pytest.raises(ValidationError):
        update_draft(issued, staff_user, extra_labour=Decimal("99.00"))


def test_reject_does_not_unlock(issued, staff_user):
    reject_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.status == Proforma.Status.ISSUED
    assert issued.rejected_at is not None
    assert ActivityLog.objects.filter(action="reject_proforma").exists()
    with pytest.raises(ValidationError):
        update_draft(issued, staff_user, observations="nope")


def test_accept_sets_accepted_at(issued, staff_user):
    accept_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.accepted_at is not None
    assert issued.status == Proforma.Status.ISSUED
    assert ActivityLog.objects.filter(action="accept_proforma").exists()


def test_unaccept_clears_accepted_at(issued, staff_user):
    accept_proforma(issued, staff_user)
    unaccept_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.accepted_at is None
    assert ActivityLog.objects.filter(action="unaccept_proforma").exists()


def test_accept_only_on_issued(staff_user, site, indoor):
    draft = create_draft(site, staff_user)
    add_line(draft, indoor, staff_user, quantity=1)
    with pytest.raises(ValidationError, match="issued"):
        accept_proforma(draft, staff_user)


def test_accept_rejected_when_already_accepted(issued, staff_user):
    accept_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="already"):
        accept_proforma(issued, staff_user)


def test_reject_sets_rejected_at(issued, staff_user):
    reject_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.rejected_at is not None
    assert issued.status == Proforma.Status.ISSUED
    assert ActivityLog.objects.filter(action="reject_proforma").exists()


def test_unreject_clears_rejected_at(issued, staff_user):
    reject_proforma(issued, staff_user)
    unreject_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert issued.rejected_at is None
    assert ActivityLog.objects.filter(action="unreject_proforma").exists()


def test_reject_only_on_issued(staff_user, site, indoor):
    draft = create_draft(site, staff_user)
    add_line(draft, indoor, staff_user, quantity=1)
    with pytest.raises(ValidationError, match="issued"):
        reject_proforma(draft, staff_user)


def test_reject_refused_when_accepted(issued, staff_user):
    accept_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="Accepted"):
        reject_proforma(issued, staff_user)


def test_accept_refused_when_rejected(issued, staff_user):
    reject_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="Rejected"):
        accept_proforma(issued, staff_user)


def test_reject_rejected_when_already_rejected(issued, staff_user):
    reject_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="already"):
        reject_proforma(issued, staff_user)
