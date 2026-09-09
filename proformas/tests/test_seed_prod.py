from io import StringIO
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from proformas.models import Client
from proformas.seed import (
    AGENT_ADMIN_EMAIL,
    AGENT_EMAIL,
    DEMO_PASSWORD,
)
from proformas.services import delete_client, save_client

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_seed_prod_idempotent_creates_agent_users():
    call_command(
        "seed_prod",
        "--password",
        "staff-secret",
        "--admin-password",
        "admin-secret",
    )
    call_command(
        "seed_prod",
        "--password",
        "staff-secret",
        "--admin-password",
        "admin-secret",
    )
    staff = User.objects.get(email=AGENT_EMAIL)
    admin = User.objects.get(email=AGENT_ADMIN_EMAIL)
    assert staff.role == User.Role.STAFF
    assert not staff.can_delete
    assert admin.role == User.Role.ADMIN
    assert admin.can_delete
    assert admin.is_superuser
    assert User.objects.filter(email=AGENT_EMAIL).count() == 1
    assert User.objects.filter(email=AGENT_ADMIN_EMAIL).count() == 1


def test_seed_prod_reads_env_when_flags_omitted():
    def fake_config(key, default=""):
        values = {
            "AGENT_PASSWORD": "from-env-staff",
            "AGENT_ADMIN_PASSWORD": "from-env-admin",
        }
        return values.get(key, default)

    with patch("proformas.seed.config", side_effect=fake_config):
        call_command("seed_prod")
    staff = User.objects.get(email=AGENT_EMAIL)
    assert staff.check_password("from-env-staff")
    admin = User.objects.get(email=AGENT_ADMIN_EMAIL)
    assert admin.check_password("from-env-admin")


def test_seed_prod_requires_passwords():
    with patch("proformas.seed.config", return_value=""):
        with pytest.raises(CommandError, match="Missing"):
            call_command("seed_prod", stdout=StringIO())


def test_agent_staff_cannot_delete_client():
    call_command(
        "seed_prod",
        "--password",
        "staff-secret",
        "--admin-password",
        "admin-secret",
    )
    staff = User.objects.get(email=AGENT_EMAIL)
    client = Client(
        kind=Client.Kind.PERSON,
        name="Temp",
        tax_number="",
        street="Rua 1",
        postal_code="1000-001",
        city="Lisboa",
        country_code="PT",
        phone_country_id="PT",
        phone="910000001",
        email="temp@example.com",
    )
    save_client(client, staff)
    from django.core.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        delete_client(client, staff)
    assert Client.objects.filter(pk=client.pk).exists()


def test_agent_admin_can_delete_client():
    call_command(
        "seed_prod",
        "--password",
        "staff-secret",
        "--admin-password",
        "admin-secret",
    )
    admin = User.objects.get(email=AGENT_ADMIN_EMAIL)
    client = Client(
        kind=Client.Kind.PERSON,
        name="Temp Admin Delete",
        tax_number="",
        street="Rua 1",
        postal_code="1000-001",
        city="Lisboa",
        country_code="PT",
        phone_country_id="PT",
        phone="910000002",
        email="temp-admin@example.com",
    )
    save_client(client, admin)
    delete_client(client, admin)
    assert not Client.objects.filter(pk=client.pk).exists()


def test_seed_prod_refuses_demo_password_when_not_debug():
    with patch.object(settings, "DEBUG", False), patch.object(
        settings, "TESTING", False
    ):
        with pytest.raises(CommandError, match="demo password"):
            call_command(
                "seed_prod",
                "--password",
                DEMO_PASSWORD,
                "--admin-password",
                "admin-secret",
                stdout=StringIO(),
            )


def test_seed_demo_refuses_when_not_debug():
    with patch.object(settings, "DEBUG", False), patch.object(
        settings, "TESTING", False
    ):
        with pytest.raises(CommandError, match="local development only"):
            call_command("seed_demo", stdout=StringIO())
