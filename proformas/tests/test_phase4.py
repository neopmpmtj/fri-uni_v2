import pytest
from django.urls import reverse

from accounts.models import User
from proformas.models import Client, Site

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )


def client_post(**overrides):
    data = {
        "kind": "person",
        "name": "Acme",
        "tax_number": "512345678",
        "street": "Rua A 1",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
        "phone": "910000001",
        "email": "acme@example.com",
    }
    data.update(overrides)
    return data


def test_staff_can_create_client_and_site(client, staff_user):
    client.force_login(staff_user)
    response = client.post(reverse("client_list"), client_post())
    assert response.status_code == 302
    org = Client.objects.get(name="Acme")
    assert Site.objects.filter(client=org, is_headquarters=True).exists()
    response = client.post(
        reverse("site_list"),
        {
            "client": org.pk,
            **{
                "alias_1": "House 1",
                "alias_2": "",
                "alias_3": "",
                "alias_4": "",
                "street": "Rua Obra 2",
                "postal_code": "1000-002",
                "city": "Lisboa",
                "phone": "920000004",
                "email": "house1@example.com",
                "contact_name": "",
                "contact_position": "",
                "notes": "",
            },
        },
    )
    assert response.status_code == 302
    assert Site.objects.filter(alias_1="House 1", client=org).exists()


def test_duplicate_live_client_name_rejected(client, staff_user):
    Client.objects.create(
        kind=Client.Kind.PERSON,
        name="Acme",
        tax_number="501442600",
        street="Rua X",
        postal_code="1000-001",
        city="Lisboa",
        country_code="PT",
        phone_country_id="PT",
        phone="910000002",
        email="existing@example.com",
    )
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        client_post(tax_number="987654322"),
    )
    assert response.status_code == 200
    assert Client.objects.filter(name="Acme").count() == 1
    assert b"already exists" in response.content
