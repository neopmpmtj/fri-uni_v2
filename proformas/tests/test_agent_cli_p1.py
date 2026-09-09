import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User
from proformas.models import Client, Site

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _payload(stdout):
    return json.loads(stdout.getvalue())


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


def test_client_save_creates_client_and_hq_site(staff_user):
    out = StringIO()
    call_command(
        "client_save",
        "--user",
        staff_user.email,
        "--kind",
        "company",
        "--name",
        "Nova Lda",
        "--nif",
        "501442600",
        "--street",
        "Rua Nova 1",
        "--postal-code",
        "1000-001",
        "--city",
        "Lisboa",
        "--phone",
        "910000099",
        "--email",
        "nova@example.com",
        stdout=out,
    )
    payload = _payload(out)
    assert payload["ok"] is True
    client = Client.objects.get(name="Nova Lda")
    assert payload["item"]["id"] == client.pk
    assert payload["item"]["tax_number"] == "501442600"
    hq = Site.objects.get(client=client, is_headquarters=True)
    assert hq.alias_1 == "Nova Lda"
    assert hq.phone == "910000099"


def test_staff_cannot_client_delete(staff_user, site):
    out = StringIO()
    with pytest.raises(CommandError, match="Only admin can delete"):
        call_command(
            "client_delete",
            "--user",
            staff_user.email,
            "--id",
            str(site.client_id),
            stdout=out,
        )
    payload = _payload(out)
    assert payload["ok"] is False
    assert Client.objects.filter(pk=site.client_id).exists()


def test_site_save_and_admin_delete(staff_user, admin_user, site):
    out = StringIO()
    call_command(
        "site_save",
        "--user",
        staff_user.email,
        "--client",
        str(site.client_id),
        "--alias-1",
        "Armazem",
        "--street",
        "Rua C 3",
        "--postal-code",
        "1000-003",
        "--city",
        "Lisboa",
        "--phone",
        "930000003",
        "--email",
        "armazem@example.com",
        stdout=out,
    )
    payload = _payload(out)
    assert payload["ok"] is True
    extra = Site.objects.get(pk=payload["item"]["id"])
    assert extra.alias_1 == "Armazem"
    assert extra.is_headquarters is False

    out = StringIO()
    call_command(
        "site_delete",
        "--user",
        admin_user.email,
        "--id",
        str(extra.pk),
        stdout=out,
    )
    deleted = _payload(out)
    assert deleted["ok"] is True
    assert deleted["item"]["deleted"] is True
    assert not Site.objects.filter(pk=extra.pk).exists()
