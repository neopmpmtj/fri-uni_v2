from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from proformas.models import Client, Proforma, Site
from proformas.seed import DEMO_ADMIN_EMAIL, DEMO_MANAGER_EMAIL, DEMO_PASSWORD

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_seed_demo_creates_users_clients_and_quotes():
    call_command("seed_demo")
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    assert admin.role == User.Role.ADMIN
    assert admin.can_delete
    assert manager.role == User.Role.STAFF
    assert not manager.can_delete
    assert User.objects.filter(email=DEMO_ADMIN_EMAIL).count() == 1
    assert Client.objects.count() == 3
    assert Site.objects.count() == 9
    assert Proforma.objects.filter(status=Proforma.Status.ISSUED).count() == 4
    assert Proforma.objects.filter(status=Proforma.Status.DRAFT).count() == 3
    assert Proforma.objects.filter(accepted_at__isnull=False).count() == 1
    assert Proforma.objects.filter(rejected_at__isnull=False).count() == 1
    assert Proforma.objects.filter(superseded_by__isnull=False).count() == 1
    assert Proforma.objects.filter(replaces__isnull=False).count() == 1
    assert (
        Proforma.objects.filter(
            status=Proforma.Status.ISSUED,
            accepted_at__isnull=True,
            rejected_at__isnull=True,
            superseded_by__isnull=True,
        ).count()
        == 1
    )
    assert Proforma.objects.count() == 7
    cascais = Proforma.objects.filter(
        site__alias_1="Moradia Cascais", status=Proforma.Status.ISSUED
    ).first()
    assert cascais is not None
    assert cascais.extra_tubing_metres == Decimal("8.00")
    revision = Proforma.objects.filter(replaces=cascais).first()
    assert revision is not None
    assert revision.extra_tubing_metres == Decimal("8.00")


def test_manager_cannot_delete_client(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    org = Client.objects.get(name="Construtora Atlantico, Lda.")
    client.force_login(manager)
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}
    )
    assert response.status_code == 302
    follow = client.get(response.url)
    assert b"Only admin can delete" in follow.content
    assert Client.objects.filter(pk=org.pk).exists()
    page = client.get(reverse("client_list"), {"id": str(org.pk)})
    assert page.status_code == 200
    assert b'value="delete"' not in page.content


def test_admin_can_delete_client(client):
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    client.force_login(admin)
    response = client.post(
        reverse("client_list"),
        {
            "kind": "company",
            "name": "Empty Client Ltd",
            "tax_number": "987654322",
            "street": "Rua Vazia 1",
            "postal_code": "1000-099",
            "city": "Lisboa",
            "country_code": "PT",
            "phone": "910000099",
            "email": "empty@example.com",
        },
    )
    assert response.status_code == 302
    org = Client.objects.get(name="Empty Client Ltd")
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}
    )
    assert response.status_code == 302
    assert not Client.objects.filter(pk=org.pk).exists()


def test_admin_cannot_delete_client_with_sites(client):
    call_command("seed_demo")
    admin = User.objects.get(email=DEMO_ADMIN_EMAIL)
    org = Client.objects.get(name="Residencias do Tejo, Lda.")
    client.force_login(admin)
    response = client.post(
        reverse("client_list"), {"id": str(org.pk), "action": "delete"}, follow=True
    )
    assert response.status_code == 200
    assert Client.objects.filter(pk=org.pk).exists()
    assert b"sites with proformas" in response.content


def test_manager_cannot_delete_site(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    site = Site.objects.get(alias_1="Moradia Cascais")
    client.force_login(manager)
    response = client.post(
        reverse("site_list"), {"id": str(site.pk), "action": "delete"}
    )
    assert response.status_code == 302
    follow = client.get(response.url)
    assert b"Only admin can delete" in follow.content
    assert Site.objects.filter(pk=site.pk).exists()
    page = client.get(reverse("site_list"), {"id": str(site.pk)})
    assert page.status_code == 200
    assert b'value="delete"' not in page.content


def test_manager_forbidden_on_admin(client):
    call_command("seed_demo")
    manager = User.objects.get(email=DEMO_MANAGER_EMAIL)
    client.force_login(manager)
    response = client.get("/admin/")
    assert response.status_code == 403


def test_demo_users_can_log_in(client):
    call_command("seed_demo")
    assert client.login(email=DEMO_MANAGER_EMAIL, password=DEMO_PASSWORD)
    assert client.login(email=DEMO_ADMIN_EMAIL, password=DEMO_PASSWORD)
