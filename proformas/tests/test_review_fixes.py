from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from proformas.models import ActivityLog, ChangeLog, Client, Proforma, TubingLength
from proformas.services import (
    add_line,
    create_draft,
    delete_client,
    issue_proforma,
    next_proforma_number,
    update_draft,
)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_discount_over_100_rejected(staff_user, site):
    with pytest.raises(ValidationError):
        create_draft(site, staff_user, discount_percent=Decimal("150"))


@pytest.mark.unit
@pytest.mark.django_db
def test_empty_issue_rejected(staff_user, site):
    proforma = create_draft(site, staff_user)
    with pytest.raises(ValidationError, match="no lines"):
        issue_proforma(proforma, staff_user)
    proforma.refresh_from_db()
    assert proforma.status == Proforma.Status.DRAFT


@pytest.mark.unit
@pytest.mark.django_db
def test_delete_client_with_sites_rejected(admin_user, site, indoor):
    add_line(create_draft(site, admin_user), indoor, admin_user)
    with pytest.raises(ValidationError, match="sites with proformas"):
        delete_client(site.client, admin_user)
    assert Client.objects.filter(pk=site.client.pk).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_number_after_9999(staff_user, site):
    year = timezone.now().year
    Proforma.objects.create(
        site=site,
        number=f"PF-{year}-9999",
        status=Proforma.Status.DRAFT,
        upfront_discount_percent=Decimal("10.00"),
        extra_labour=Decimal("0.00"),
        created_by=staff_user,
        updated_by=staff_user,
    )
    assert next_proforma_number() == f"PF-{year}-10000"
    created = create_draft(site, staff_user)
    assert created.number == f"PF-{year}-10000"


@pytest.mark.integration
@pytest.mark.django_db
def test_qty_zero_http_form_error(client, staff_user, site, indoor):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {
            "action": "save_line",
            "item": str(indoor.pk),
            "quantity": "0",
        },
    )
    assert response.status_code == 200
    assert proforma.lines.count() == 0


@pytest.mark.integration
@pytest.mark.django_db
def test_issue_applies_unsaved_header(client, staff_user, site, indoor):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {
            "action": "issue",
            "upfront_discount_percent": "5",
            "extra_labour": "20.00",
            "observations": "locked in",
        },
    )
    assert response.status_code == 302
    proforma.refresh_from_db()
    assert proforma.status == Proforma.Status.ISSUED
    assert proforma.upfront_discount_percent == Decimal("5.00")
    assert proforma.extra_labour == Decimal("20.00")
    assert proforma.observations == "locked in"
    assert proforma.discount_amount == Decimal("25.00")


@pytest.mark.integration
@pytest.mark.django_db
def test_issued_detail_uses_snapshot_after_rename(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    issue_proforma(proforma, staff_user)
    site.client.name = "Renamed Ltd"
    site.client.save()
    site.alias_1 = "New alias"
    site.save()
    client.force_login(staff_user)
    detail = client.get(reverse("proforma_detail", args=[proforma.pk]))
    listing = client.get(reverse("proforma_list"))
    assert b"Acme" in detail.content
    assert b"House 1" in detail.content
    assert b"Renamed Ltd" not in detail.content
    assert b"New alias" not in detail.content
    table = listing.content.split(b'<table class="grid">', 1)[1].split(b"</table>", 1)[0]
    assert b"Acme" in table
    assert b"Renamed Ltd" not in table


@pytest.mark.integration
@pytest.mark.django_db
def test_wrong_status_issue_shows_message(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    issue_proforma(proforma, staff_user)
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {
            "action": "issue",
            "upfront_discount_percent": "10",
            "extra_labour": "0",
        },
        follow=True,
    )
    assert response.status_code == 200
    assert b"Only draft proformas can be edited." in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_pricelist_without_reason_is_form_error(client, admin_user, indoor):
    client.force_login(admin_user)
    url = reverse("manufacturer_pricelist", args=[indoor.brand_id])
    response = client.post(
        url,
        {
            "id": str(indoor.pk),
            "list_price": "510.00",
            "reason": "",
        },
    )
    assert response.status_code == 200
    indoor.refresh_from_db()
    assert indoor.list_price == Decimal("500.00")
    assert ChangeLog.objects.filter(field="list_price").count() == 0
    assert response.context["form"].errors.get("reason")


@pytest.mark.unit
@pytest.mark.django_db
def test_create_draft_writes_activity_log(staff_user, site):
    proforma = create_draft(site, staff_user)
    assert ActivityLog.objects.filter(
        action="create_proforma", object_id=proforma.pk
    ).exists()


@pytest.mark.unit
@pytest.mark.django_db
def test_update_draft_rejects_negative_labour(staff_user, site):
    proforma = create_draft(site, staff_user)
    with pytest.raises(ValidationError):
        update_draft(proforma, staff_user, extra_labour=Decimal("-1.00"))


@pytest.mark.integration
@pytest.mark.django_db
def test_new_line_drawer_defaults_shortest_tubing_length(
    client, staff_user, site, indoor, tubing
):
    short = TubingLength.objects.create(length=Decimal("3.00"), price=Decimal("25.00"))
    TubingLength.objects.create(length=Decimal("10.00"), price=Decimal("70.00"))
    proforma = create_draft(site, staff_user)
    client.force_login(staff_user)
    response = client.get(
        reverse("proforma_detail", args=[proforma.pk]), {"new_line": "1"}
    )
    assert response.status_code == 200
    assert b"tubing-length-field" in response.content
    field = response.context["line_form"].fields["tubing_length"]
    assert field.empty_label is None
    assert field.initial == short
    html = response.content.decode()
    assert f'value="{short.pk}" selected' in html
