import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from proformas.models import Power, Proforma
from proformas.services import add_line, create_draft, issue_proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _payload(stdout):
    return json.loads(stdout.getvalue())


def test_client_list_search_envelope(site):
    out = StringIO()
    call_command("client_list", "--search", "Acme", stdout=out)
    payload = _payload(out)
    assert payload["ok"] is True
    assert payload["entity"] == "client"
    assert payload["limit"] == 25
    assert payload["offset"] == 0
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == site.client_id
    assert payload["items"][0]["label"] == "Acme"


def test_client_show_unknown_id():
    out = StringIO()
    with pytest.raises(CommandError, match="Unknown client"):
        call_command("client_show", "99999", stdout=out)
    payload = _payload(out)
    assert payload["ok"] is False
    assert "Unknown client" in payload["error"]


def test_item_list_kind_indoor_money_strings(indoor):
    out = StringIO()
    call_command("item_list", "--kind", "indoor", stdout=out)
    payload = _payload(out)
    assert payload["ok"] is True
    assert payload["count"] == 1
    row = payload["items"][0]
    assert row["kind"] == "indoor"
    assert row["internal_code"] == "MIT-SPL-I-9"
    assert row["list_price"] == "500.00"


def test_power_list_volume_band(indoor):
    power = indoor.power
    power.volume_from_m3 = Decimal("0")
    power.volume_to_m3 = Decimal("20")
    power.default_indoor = indoor
    power.save()
    other, _ = Power.objects.get_or_create(power=12000, unit="BTU")
    other.volume_from_m3 = Decimal("21")
    other.volume_to_m3 = Decimal("35")
    other.save()

    out = StringIO()
    call_command("power_list", "--volume", "15", stdout=out)
    payload = _payload(out)
    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == power.pk
    assert payload["items"][0]["default_indoor_code"] == indoor.internal_code


def test_proforma_list_marks_expired(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    issue_proforma(proforma, staff_user)
    proforma.valid_until = timezone.localdate() - timedelta(days=1)
    proforma.save(update_fields=["valid_until"])

    out = StringIO()
    call_command("proforma_list", "--status", "issued", stdout=out)
    payload = _payload(out)
    assert payload["ok"] is True
    row = payload["items"][0]
    assert row["number"] == proforma.number
    assert row["expired"] is True
    assert Proforma.objects.get(pk=proforma.pk).status == Proforma.Status.ISSUED
