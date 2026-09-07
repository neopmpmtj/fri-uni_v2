import pytest
from django.urls import reverse

from proformas.services import add_line, create_draft, issue_proforma, reject_proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def issued(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_post_mark_rejected_on_issued_detail(client, staff_user, issued):
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[issued.pk]),
        {"action": "reject_proforma"},
    )
    assert response.status_code == 302
    issued.refresh_from_db()
    assert issued.rejected_at is not None
    assert issued.status == "issued"

    page = client.get(reverse("proforma_detail", args=[issued.pk]))
    assert page.status_code == 200
    assert b"status-pill--rejected" in page.content
    assert b"Clear rejected" in page.content
    assert b"Mark accepted" not in page.content


def test_post_unreject_on_issued_detail(client, staff_user, issued):
    reject_proforma(issued, staff_user)
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[issued.pk]),
        {"action": "unreject_proforma"},
    )
    assert response.status_code == 302
    issued.refresh_from_db()
    assert issued.rejected_at is None

    page = client.get(reverse("proforma_detail", args=[issued.pk]))
    assert page.status_code == 200
    assert b"Mark rejected" in page.content
    assert b"Mark accepted" in page.content


def test_list_post_mark_rejected(client, staff_user, issued):
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_outcome"),
        {"id": str(issued.pk), "action": "reject_proforma"},
    )
    assert response.status_code == 302
    assert response.url == reverse("proforma_list")
    issued.refresh_from_db()
    assert issued.rejected_at is not None

    listing = client.get(reverse("proforma_list"))
    assert b"Clear rejected" in listing.content
    assert b"Change" not in listing.content
    assert b"outcome-icon--accept" not in listing.content
    assert b"outcome-icon--reject" not in listing.content


def test_list_post_clear_rejected(client, staff_user, issued):
    reject_proforma(issued, staff_user)
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_outcome"),
        {"id": str(issued.pk), "action": "unreject_proforma"},
    )
    assert response.status_code == 302
    issued.refresh_from_db()
    assert issued.rejected_at is None

    listing = client.get(reverse("proforma_list"))
    assert b"Change" in listing.content
    assert b"outcome-icon--reject" in listing.content
    assert b"Clear rejected" not in listing.content


def test_list_status_choices_are_draft_and_issued(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("proforma_list"))
    assert response.status_code == 200
    values = [value for value, _label in response.context["status_choices"]]
    assert values == ["draft", "issued"]


def test_list_shows_rejected_pill_and_no_change(client, staff_user, issued):
    reject_proforma(issued, staff_user)
    client.force_login(staff_user)
    listing = client.get(reverse("proforma_list"))
    assert listing.status_code == 200
    assert b"status-pill--rejected" in listing.content
    assert b'<button type="submit" class="btn-link" data-i18n="change">Change</button>' not in listing.content
    assert b"Clear rejected" in listing.content
    assert b"outcome-icon--accept" not in listing.content
    assert b"outcome-icon--reject" not in listing.content
