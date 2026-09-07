from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from proformas.models import ActivityLog, Proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


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
    proforma = Proforma.objects.get(number=out.getvalue().strip())
    assert proforma.created_by == staff_user
    assert proforma.status == Proforma.Status.DRAFT
    assert proforma.lines.count() == 1
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
    proforma = Proforma.objects.get(number=out.getvalue().strip())
    assert proforma.status == Proforma.Status.ISSUED
    assert proforma.grand_total is not None
    assert proforma.client_name == "Acme"


def test_cli_unknown_user_or_site_fails(staff_user, site, indoor):
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            "missing@example.com",
            "--site",
            str(site.pk),
            "--line",
            f"{indoor.pk}:1",
        )
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            "99999",
            "--line",
            f"{indoor.pk}:1",
        )


def test_cli_unknown_model_does_not_leave_draft(staff_user, site, indoor):
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
        )
    assert Proforma.objects.count() == 0


def test_cli_bad_line_spec(staff_user, site, indoor):
    with pytest.raises(CommandError):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            str(site.pk),
            "--line",
            "not-an-id:1",
        )


def test_cli_inactive_user_fails(staff_user, site, indoor):
    staff_user.is_active = False
    staff_user.save(update_fields=["is_active"])
    with pytest.raises(CommandError, match="Inactive user"):
        call_command(
            "create_proforma",
            "--user",
            staff_user.email,
            "--site",
            str(site.pk),
            "--line",
            f"{indoor.pk}:1",
        )
