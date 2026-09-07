import pytest
from django.urls import reverse

from proformas.services import add_line, create_draft, issue_proforma

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _issued(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


def test_quote_html_uses_snapshot_client_name(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    site.client.name = "Renamed Ltd"
    site.client.save()
    client.force_login(staff_user)
    response = client.get(reverse("proforma_quote", args=[proforma.pk]))
    assert response.status_code == 200
    body = response.content.decode()
    assert "Acme" in body
    assert "Renamed Ltd" not in body


def test_pdf_download(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    response = client.get(reverse("proforma_pdf", args=[proforma.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert len(response.content) > 0


def test_portuguese_quote_label(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    client.cookies["fu-lang"] = "pt"
    response = client.get(reverse("proforma_quote", args=[proforma.pk]))
    assert "Totais" in response.content.decode()
    pdf = client.get(reverse("proforma_pdf", args=[proforma.pk]))
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert len(pdf.content) > 0
    from django.template.loader import render_to_string

    from proformas.quote_i18n import quote_labels

    html = render_to_string(
        "proformas/quote_pdf.html",
        {
            "proforma": proforma,
            "lines": proforma.lines.all(),
            "labels": quote_labels("pt"),
            "company_name": "fri-uni",
            "html_lang": "pt-PT",
        },
    )
    assert "Totais" in html
    assert 'lang="pt-PT"' in html


def test_quote_includes_extra_site_snapshots(client, staff_user, site, indoor):
    site.alias_3 = "Gate C"
    site.notes = "Bring ladder"
    site.save()
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "Gate C" in body
    assert "Bring ladder" in body


def test_quote_shows_stored_extra_tubing_metres(client, staff_user, site, indoor, tubing):
    proforma = create_draft(site, staff_user, discount_percent=0)
    add_line(
        proforma,
        indoor,
        staff_user,
        quantity=2,
        extra_tubing=True,
        tubing_length=tubing,
    )
    issued = issue_proforma(proforma, staff_user)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[issued.pk])).content.decode()
    assert "10.00 m" in body

