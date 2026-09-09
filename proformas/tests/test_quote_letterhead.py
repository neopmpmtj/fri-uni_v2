from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.urls import reverse
from PIL import Image

from proformas.services import (
    add_line,
    create_draft,
    display_iban,
    get_company,
    issue_proforma,
    quote_template_context,
    save_company,
)

VALID_IBAN = "PT50000201231234567890154"


def _issued(staff_user, site, indoor):
    proforma = create_draft(site, staff_user, discount_percent=10)
    add_line(proforma, indoor, staff_user, quantity=1)
    return issue_proforma(proforma, staff_user)


@pytest.mark.unit
def test_display_iban_groups_characters():
    assert display_iban(VALID_IBAN) == "PT50 0002 0123 1234 5678 9015 4"
    assert display_iban("") == ""


@pytest.mark.integration
@pytest.mark.django_db
def test_quote_html_uses_live_company(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "Fribila" in body
    assert "Rua da Promaça" in body
    assert "5000-081" in body
    assert "Vila Real" in body
    assert "259326314" in body
    assert "Chamada para a rede fixa nacional" in body
    assert "info@fribila.pt" in body
    assert "fri-uni" not in body
    assert "IBAN" not in body
    assert "Contact:" not in body


@pytest.mark.integration
@pytest.mark.django_db
def test_quote_html_reads_company_after_issue(client, staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    company = get_company()
    company.name = "Renamed Issuer"
    company.tax_number = "501442600"
    company.iban = VALID_IBAN
    company.contact_name = "Ana Costa"
    save_company(company, staff_user)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "Renamed Issuer" in body
    assert "501442600" in body
    assert "PT50 0002 0123 1234 5678 9015 4" in body
    assert "Ana Costa" in body
    assert "Fribila" not in body


@pytest.mark.integration
@pytest.mark.django_db
def test_quote_pdf_html_uses_live_company(staff_user, site, indoor):
    proforma = _issued(staff_user, site, indoor)
    html = render_to_string(
        "proformas/quote_pdf.html",
        quote_template_context(proforma, "en", absolute_logo=True),
    )
    assert "Fribila" in html
    assert "info@fribila.pt" in html
    assert "fri-uni" not in html


@pytest.mark.integration
@pytest.mark.django_db
def test_quote_html_includes_logo(
    client, staff_user, site, indoor, tmp_path, settings
):
    settings.MEDIA_ROOT = tmp_path
    buf = BytesIO()
    Image.new("RGB", (16, 16), "red").save(buf, format="PNG")
    company = get_company()
    company.logo.save("mark.png", ContentFile(buf.getvalue()), save=False)
    save_company(company, staff_user)
    proforma = _issued(staff_user, site, indoor)
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "quote-logo" in body
    assert "mark.png" in body
    pdf_html = render_to_string(
        "proformas/quote_pdf.html",
        quote_template_context(proforma, "en", absolute_logo=True),
    )
    assert pdf_html.count("mark.png") == 1
    assert "file://" in pdf_html
