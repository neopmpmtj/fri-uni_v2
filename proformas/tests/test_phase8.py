from decimal import Decimal
from io import StringIO
import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from proformas.models import ActivityLog, Proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _cli_proforma(stdout):
    payload = json.loads(stdout.getvalue())
    assert payload["ok"] is True
    return Proforma.objects.get(pk=payload["item"]["id"])


def test_cli_creates_draft_with_created_by(staff_user, site, indoor):
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
    proforma = _cli_proforma(out)
    assert proforma.created_by == staff_user
    assert proforma.status == Proforma.Status.DRAFT
    assert proforma.lines.count() == 2
    assert ActivityLog.objects.filter(
        action="create_proforma", object_id=proforma.pk
    ).exists()


def test_cli_issue_freezes(staff_user, site, indoor):
    out = StringIO()
    call_command(
        "create_proforma",
        "--user",
        staff_user.email,
        "--site",
        str(site.pk),
        "--line",
        f"{indoor.pk}:2",
        "--issue",
        stdout=out,
    )
    proforma = _cli_proforma(out)
    assert proforma.status == Proforma.Status.ISSUED
    assert proforma.grand_total is not None
    assert proforma.client_name == "Acme"


def test_cli_discount_flags(staff_user, site, indoor):
    out = StringIO()
    call_command(
        "create_proforma",
        "--user",
        staff_user.email,
        "--site",
        str(site.pk),
        "--line",
        f"{indoor.pk}:1",
        "--discount-percent",
        "10",
        "--commercial-discount-percent",
        "10",
        stdout=out,
    )
    proforma = _cli_proforma(out)
    assert proforma.financial_discount_percent == Decimal("10.00")
    assert proforma.commercial_discount_percent == Decimal("10.00")
    assert proforma.commercial_discount_amount == Decimal("105.00")
    assert proforma.financial_discount_amount == Decimal("94.50")


def test_cli_unknown_user_or_site_fails(staff_user, site, indoor):
    out = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            "missing@example.com",
            "--site",
            str(site.pk),
            "--line",
            f"{indoor.pk}:1",
            stdout=out,
        )
    out = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            "99999",
            "--line",
            f"{indoor.pk}:1",
            stdout=out,
        )


def test_cli_unknown_model_does_not_leave_draft(staff_user, site, indoor):
    out = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            str(site.pk),
            "--line",
            f"{indoor.pk}:1",
            "--line",
            "99999:1",
            stdout=out,
        )
    assert Proforma.objects.count() == 0


def test_cli_bad_line_spec(staff_user, site, indoor):
    out = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            str(site.pk),
            "--line",
            "not-an-id:1",
            stdout=out,
        )


def test_cli_inactive_user_fails(staff_user, site, indoor):
    staff_user.is_active = False
    staff_user.save(update_fields=["is_active"])
    out = StringIO()
    with pytest.raises(CommandError, match="Inactive user"):
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
