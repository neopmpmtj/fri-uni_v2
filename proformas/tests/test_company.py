import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from proformas.models import Company
from proformas.services import get_company, save_company, validate_iban


VALID_IBAN = "PT50000201231234567890154"


def company_post(**overrides):
    company = Company.objects.get()
    data = {
        "name": company.name,
        "tax_number": company.tax_number,
        "street": company.street,
        "postal_code": company.postal_code,
        "city": company.city,
        "country_code": company.country_code,
        "phone": company.phone,
        "phone_note": company.phone_note,
        "email": company.email,
        "contact_name": company.contact_name,
        "contact_position": company.contact_position_id or "",
        "iban": company.iban,
    }
    data.update(overrides)
    return data


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_seeds_one_fribila_company():
    assert Company.objects.count() == 1
    company = get_company()
    assert company.name == "Fribila"
    assert company.street == "Rua da Promaça, nº4"
    assert company.postal_code == "5000-081"
    assert company.city == "Vila Real"
    assert company.country_code == "PT"
    assert company.phone_country_id == "PT"
    assert company.phone == "259326314"
    assert company.phone_note == "Chamada para a rede fixa nacional"
    assert company.email == "info@fribila.pt"
    assert company.tax_number == ""
    assert company.iban == ""
    assert company.contact_name == ""
    assert company.contact_position_id is None
    assert not company.logo


@pytest.mark.unit
@pytest.mark.django_db
def test_save_company_rejects_second_row(staff_user):
    extra = Company(
        name="Other",
        street="Rua X",
        postal_code="1000-001",
        city="Lisboa",
        country_code="PT",
        phone_country_id="PT",
        phone="912345678",
        email="other@example.com",
    )
    with pytest.raises(ValidationError, match="Only one company profile"):
        save_company(extra, staff_user)
    assert Company.objects.count() == 1


@pytest.mark.unit
def test_validate_iban_accepts_compact_portuguese():
    assert validate_iban("PT50 0002 0123 1234 5678 9015 4") == VALID_IBAN


@pytest.mark.unit
def test_validate_iban_empty():
    assert validate_iban("") == ""
    assert validate_iban("   ") == ""


@pytest.mark.unit
def test_validate_iban_rejects_bad_checksum():
    with pytest.raises(ValidationError, match="check digits"):
        validate_iban("PT00000000000000000000000")


@pytest.mark.unit
def test_validate_iban_rejects_non_portuguese():
    with pytest.raises(ValidationError, match="Portuguese IBAN"):
        validate_iban("DE89370400440532013000")


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_can_open_company_page(client, staff_user):
    client.force_login(staff_user)
    response = client.get(reverse("company_edit"))
    assert response.status_code == 200
    assert b"Fribila" in response.content
    assert b"Delete" not in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_can_save_company(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("company_edit"),
        company_post(tax_number="501442600", iban=VALID_IBAN),
    )
    assert response.status_code == 302
    company = get_company()
    assert company.tax_number == "501442600"
    assert company.iban == VALID_IBAN
    assert Company.objects.count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_company_ten_digit_nif_rejected(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("company_edit"),
        company_post(tax_number="5014426000"),
    )
    assert response.status_code == 200
    assert b"more than 9 digits" in response.content
    assert get_company().tax_number == ""


@pytest.mark.integration
@pytest.mark.django_db
def test_company_eight_digit_nif_rejected(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("company_edit"),
        company_post(tax_number="50144260"),
    )
    assert response.status_code == 200
    assert b"fewer than 9 digits" in response.content
    assert get_company().tax_number == ""


@pytest.mark.integration
@pytest.mark.django_db
def test_company_ten_digit_phone_rejected(client, staff_user):
    client.force_login(staff_user)
    original = get_company().phone
    response = client.post(
        reverse("company_edit"),
        company_post(phone="2593263140"),
    )
    assert response.status_code == 200
    assert b"more than 9 digits" in response.content
    assert get_company().phone == original


@pytest.mark.integration
@pytest.mark.django_db
def test_company_invalid_iban_rejected(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("company_edit"),
        company_post(iban="PT00000000000000000000000"),
    )
    assert response.status_code == 200
    assert b"Invalid IBAN check digits" in response.content
    assert get_company().iban == ""


@pytest.mark.integration
@pytest.mark.django_db
def test_company_empty_iban_allowed(client, staff_user):
    client.force_login(staff_user)
    company = get_company()
    company.iban = VALID_IBAN
    company.save()
    response = client.post(reverse("company_edit"), company_post(iban=""))
    assert response.status_code == 302
    assert get_company().iban == ""
