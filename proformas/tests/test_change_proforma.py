from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from proformas.models import ActivityLog, Proforma
from proformas.services import (
    accept_proforma,
    add_line,
    change_proforma,
    create_draft,
    is_active_for_stats,
    issue_proforma,
    reject_proforma,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def issued(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=2)
    return issue_proforma(proforma, staff_user)


@pytest.mark.unit
def test_change_creates_draft_with_links(issued, staff_user):
    frozen_total = issued.grand_total
    frozen_unit = issued.lines.first().unit_price
    new = change_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert new.status == Proforma.Status.DRAFT
    assert new.number != issued.number
    assert new.replaces_id == issued.pk
    assert issued.superseded_by_id == new.pk
    assert issued.status == Proforma.Status.ISSUED
    assert issued.grand_total == frozen_total
    assert issued.lines.first().unit_price == frozen_unit
    assert new.lines.count() == issued.lines.count()
    assert ActivityLog.objects.filter(action="change_proforma").exists()


@pytest.mark.unit
def test_change_rejected_on_draft(staff_user, site, indoor):
    draft = create_draft(site, staff_user)
    add_line(draft, indoor, staff_user)
    with pytest.raises(ValidationError, match="issued"):
        change_proforma(draft, staff_user)


@pytest.mark.unit
def test_change_rejected_when_rejected(issued, staff_user):
    reject_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="Rejected"):
        change_proforma(issued, staff_user)


@pytest.mark.unit
def test_change_rejected_when_accepted(issued, staff_user):
    accept_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="Accepted"):
        change_proforma(issued, staff_user)


@pytest.mark.unit
def test_change_rejected_when_already_superseded(issued, staff_user):
    change_proforma(issued, staff_user)
    with pytest.raises(ValidationError, match="already"):
        change_proforma(issued, staff_user)


@pytest.mark.unit
def test_is_active_for_stats(issued, staff_user):
    assert is_active_for_stats(issued) is True
    change_proforma(issued, staff_user)
    issued.refresh_from_db()
    assert is_active_for_stats(issued) is False


@pytest.mark.integration
def test_list_change_and_superseded_pill(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user)
    issue_proforma(proforma, staff_user)
    client.force_login(staff_user)

    listing = client.get(reverse("proforma_list"))
    assert listing.status_code == 200
    assert b"Change" in listing.content

    response = client.post(
        reverse("proforma_change"),
        {"id": str(proforma.pk)},
    )
    assert response.status_code == 302
    new = Proforma.objects.get(replaces_id=proforma.pk)
    assert response.url == reverse("proforma_detail", args=[new.pk])

    listing = client.get(reverse("proforma_list"))
    assert b"status-pill--superseded" in listing.content


@pytest.mark.integration
def test_list_edit_for_draft_and_no_change_when_accepted(
    client, staff_user, site, indoor
):
    create_draft(site, staff_user)
    accepted = create_draft(site, staff_user)
    add_line(accepted, indoor, staff_user)
    issue_proforma(accepted, staff_user)
    accept_proforma(accepted, staff_user)
    client.force_login(staff_user)

    listing = client.get(reverse("proforma_list"))
    assert listing.status_code == 200
    assert b"Edit" in listing.content
    assert b'<button type="submit" class="btn-link" data-i18n="change">Change</button>' not in listing.content
    assert b"Clear accepted" in listing.content
    assert b"outcome-icon--accept" not in listing.content
    assert b"outcome-icon--reject" not in listing.content
