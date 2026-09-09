import json
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from proformas.models import Item, Proforma, ProformaLine
from proformas.services import add_line, create_draft

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _payload(stdout):
    return json.loads(stdout.getvalue())


def _set_band(power, volume_from, volume_to, indoor=None):
    power.volume_from_m3 = Decimal(str(volume_from))
    power.volume_to_m3 = Decimal(str(volume_to))
    if indoor is not None:
        power.default_indoor = indoor
    power.save()
    return power


def test_create_proforma_volume_m3(staff_user, site, indoor):
    _set_band(indoor.power, 0, 20, indoor)
    out = StringIO()
    call_command(
        "create_proforma",
        "--user",
        staff_user.email,
        "--site",
        str(site.pk),
        "--volume-m3",
        "15",
        stdout=out,
    )
    payload = _payload(out)
    assert payload["ok"] is True
    assert payload["item"]["status"] == "draft"
    proforma = Proforma.objects.get(pk=payload["item"]["id"])
    indoor_lines = [
        line
        for line in proforma.lines.select_related("item")
        if line.item.kind == Item.Kind.INDOOR
    ]
    assert len(indoor_lines) == 1
    assert indoor_lines[0].item_id == indoor.pk
    assert proforma.lines.count() == 2


def test_create_proforma_rejects_line_and_volume(staff_user, site, indoor):
    out = StringIO()
    with pytest.raises(CommandError, match="not both"):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            str(site.pk),
            "--volume-m3",
            "15",
            "--line",
            f"{indoor.pk}:1",
            stdout=out,
        )
    assert Proforma.objects.count() == 0


def test_add_update_remove_line(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    out = StringIO()
    call_command(
        "proforma_add_line",
        "--user",
        staff_user.email,
        "--proforma",
        str(proforma.pk),
        "--item",
        str(indoor.pk),
        "--qty",
        "1",
        stdout=out,
    )
    payload = _payload(out)
    assert payload["ok"] is True
    indoor_line = next(
        line
        for line in proforma.lines.select_related("item")
        if line.item.kind == Item.Kind.INDOOR
    )
    out = StringIO()
    call_command(
        "proforma_update_line",
        "--user",
        staff_user.email,
        "--id",
        str(indoor_line.pk),
        "--qty",
        "3",
        stdout=out,
    )
    payload = _payload(out)
    assert payload["ok"] is True
    indoor_line.refresh_from_db()
    assert indoor_line.quantity == 3

    out = StringIO()
    call_command(
        "proforma_remove_line",
        "--user",
        staff_user.email,
        "--id",
        str(indoor_line.pk),
        stdout=out,
    )
    assert _payload(out)["ok"] is True
    assert not ProformaLine.objects.filter(pk=indoor_line.pk).exists()


def test_issue_accept_and_pdf(staff_user, site, indoor, tmp_path):
    out = StringIO()
    call_command(
        "create_proforma",
        "--user",
        staff_user.email,
        "--site",
        str(site.pk),
        "--line",
        f"{indoor.pk}:1",
        stdout=out,
    )
    pk = _payload(out)["item"]["id"]

    out = StringIO()
    call_command(
        "proforma_issue",
        "--user",
        staff_user.email,
        "--proforma",
        str(pk),
        stdout=out,
    )
    issued = _payload(out)
    assert issued["item"]["status"] == "issued"
    assert issued["item"]["expired"] is False

    out = StringIO()
    call_command(
        "proforma_accept",
        "--user",
        staff_user.email,
        "--proforma",
        str(pk),
        stdout=out,
    )
    assert _payload(out)["item"]["accepted"] is True

    pdf_path = tmp_path / "quote.pdf"
    out = StringIO()
    call_command(
        "proforma_pdf",
        "--user",
        staff_user.email,
        "--proforma",
        str(pk),
        "--out",
        str(pdf_path),
        stdout=out,
    )
    pdf_payload = _payload(out)
    assert pdf_payload["ok"] is True
    assert pdf_payload["item"]["bytes"] > 0
    assert pdf_path.read_bytes()[:4] == b"%PDF"


def test_pdf_rejects_draft(staff_user, site, indoor, tmp_path):
    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user, quantity=1)
    out = StringIO()
    with pytest.raises(CommandError, match="issued"):
        call_command(
            "proforma_pdf",
            "--user",
            staff_user.email,
            "--proforma",
            str(proforma.pk),
            "--out",
            str(tmp_path / "nope.pdf"),
            stdout=out,
        )
    assert not (tmp_path / "nope.pdf").exists()
