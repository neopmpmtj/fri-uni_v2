import pytest
from django.db import IntegrityError

from proformas.models import Client

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _client(**kwargs):
    data = {
        "kind": Client.Kind.PERSON,
        "name": "Acme",
        "tax_number": "512345678",
        "street": "Rua A 1",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
        "phone_country_id": "PT",
        "phone": "910000001",
        "email": "acme@example.com",
    }
    data.update(kwargs)
    return Client.objects.create(**data)


def test_live_client_name_must_be_unique():
    _client()
    with pytest.raises(IntegrityError):
        _client(tax_number="987654322")


def test_soft_deleted_client_name_can_be_reused():
    first = _client()
    first.soft_delete()
    _client(tax_number="987654322")
    assert Client.objects.filter(name="Acme").count() == 1
    assert Client.all_objects.filter(name="Acme").count() == 2
