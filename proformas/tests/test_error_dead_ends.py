from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from accounts.models import User
from proformas.models import Parameter, Proforma
from proformas.services import add_line, create_draft, delete_item, issue_proforma


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_pdf_build_error_redirects(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    issue_proforma(proforma, staff_user)
    client.force_login(staff_user)
    with patch(
        "proformas.views.build_proforma_pdf",
        side_effect=ValidationError("Could not generate PDF."),
    ):
        response = client.get(reverse("proforma_pdf", args=[proforma.pk]))
    assert response.status_code == 302
    assert response.url == reverse("proforma_detail", args=[proforma.pk])


@pytest.mark.integration
@pytest.mark.django_db
def test_create_draft_validation_error_reopens_drawer(client, staff_user, site):
    Parameter.objects.update_or_create(
        key="default_upfront_discount_percent",
        defaults={"value": "not-a-number"},
    )
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_list"),
        {
            "action": "create",
            "client": str(site.client.pk),
            "site": str(site.pk),
        },
    )
    assert response.status_code == 200
    assert site.proformas.filter(status=Proforma.Status.DRAFT).count() == 0
    assert b"Enter a valid discount percent" in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_invalid_issue_header_shows_message(client, staff_user, site, indoor):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {
            "action": "issue",
            "upfront_discount_percent": "150",
            "extra_labour": "0",
            "observations": "",
        },
    )
    assert response.status_code == 200
    assert proforma.status == Proforma.Status.DRAFT
    assert b"Fix the header fields before issuing" in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_delete_client_shows_message_not_403(client, staff_user, site):
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        {"action": "delete", "id": str(site.client.pk)},
    )
    assert response.status_code == 302
    follow = client.get(response.url)
    assert b"Only admin can delete" in follow.content


@pytest.mark.unit
@pytest.mark.django_db
def test_delete_item_used_on_line_rejected(admin_user, site, indoor):
    proforma = create_draft(site, admin_user)
    add_line(proforma, indoor, admin_user, quantity=1)
    with pytest.raises(ValidationError, match="proforma line"):
        delete_item(indoor, admin_user)


@pytest.mark.unit
@pytest.mark.django_db
def test_parameter_form_rejects_invalid_default_discount():
    from proformas.forms import ParameterForm

    parameter, _ = Parameter.objects.get_or_create(
        key="default_upfront_discount_percent",
        defaults={"value": "10"},
    )
    form = ParameterForm({"value": "150"}, instance=parameter)
    assert not form.is_valid()
    assert "value" in form.errors


@pytest.mark.integration
@pytest.mark.django_db
def test_accept_proforma_via_post(client, staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    issue_proforma(proforma, staff_user)
    client.force_login(staff_user)
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {"action": "accept_proforma"},
    )
    assert response.status_code == 302
    proforma.refresh_from_db()
    assert proforma.accepted_at is not None
