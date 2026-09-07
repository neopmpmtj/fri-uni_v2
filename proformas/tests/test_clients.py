import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from accounts.models import User
from proformas.forms import SiteForm
from proformas.models import Client, Site
from proformas.services import (
    normalize_postal_code,
    save_client,
    validate_phone_number,
    validate_tax_number,
)


def client_kwargs(**overrides):
    data = {
        "kind": Client.Kind.PERSON,
        "name": "Acme",
        "tax_number": "512345678",
        "street": "Rua Teste 1",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
        "phone_country_id": "PT",
        "phone": "910000001",
        "email": "acme@example.com",
    }
    data.update(overrides)
    return data


def site_post(**overrides):
    data = {
        "alias_1": "Obra",
        "alias_2": "",
        "alias_3": "",
        "alias_4": "",
        "street": "Rua B",
        "postal_code": "1000-003",
        "city": "Lisboa",
        "phone": "930000003",
        "email": "site@example.com",
        "contact_name": "",
        "contact_position": "",
        "notes": "",
    }
    data.update(overrides)
    return data


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_accepts_dash():
    assert normalize_postal_code("1000-001") == "1000-001"


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_inserts_dash():
    assert normalize_postal_code("1000001") == "1000-001"


@pytest.mark.unit
@pytest.mark.django_db
def test_normalize_postal_code_rejects_bad_length():
    with pytest.raises(ValidationError):
        normalize_postal_code("10000")


@pytest.mark.unit
@pytest.mark.django_db
def test_validate_tax_number_checksum():
    assert validate_tax_number("501442600") == "501442600"


@pytest.mark.unit
@pytest.mark.django_db
def test_validate_tax_number_rejects_bad_checksum():
    with pytest.raises(ValidationError):
        validate_tax_number("501442601")


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("12345678", "fewer than 9"),
        ("1234567890", "more than 9"),
    ],
)
def test_validate_tax_number_rejects_wrong_length(value, message):
    with pytest.raises(ValidationError, match=message):
        validate_tax_number(value)


@pytest.mark.unit
@pytest.mark.django_db
def test_validate_phone_number_accepts_nine_digits():
    assert validate_phone_number("912345678") == "912345678"


@pytest.mark.unit
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("12345678", "fewer than 9"),
        ("1234567890", "more than 9"),
    ],
)
def test_validate_phone_number_rejects_wrong_length(value, message):
    with pytest.raises(ValidationError, match=message):
        validate_phone_number(value)


@pytest.mark.unit
@pytest.mark.django_db
def test_multiple_clients_may_have_blank_tax_number(staff_user):
    first = Client(**client_kwargs(name="First", tax_number=""))
    second = Client(**client_kwargs(name="Second", tax_number=""))
    save_client(first, staff_user)
    save_client(second, staff_user)
    assert Client.objects.filter(tax_number="").count() == 2


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        email="staff@example.com", password="pass12345", role=User.Role.STAFF
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_save_client_creates_hq_site(staff_user):
    client = Client(**client_kwargs())
    save_client(client, staff_user)
    hq = Site.objects.get(client=client, is_headquarters=True)
    assert hq.alias_1 == "Acme"
    assert hq.street == client.street
    assert hq.postal_code == client.postal_code
    assert hq.city == client.city


@pytest.mark.unit
@pytest.mark.django_db
def test_save_client_edit_does_not_rewrite_hq(staff_user):
    client = Client(**client_kwargs())
    save_client(client, staff_user)
    hq = Site.objects.get(client=client, is_headquarters=True)
    client.name = "Renamed"
    client.street = "Other street"
    save_client(client, staff_user)
    hq.refresh_from_db()
    assert hq.alias_1 == "Acme"
    assert hq.street == "Rua Teste 1"


@pytest.mark.unit
@pytest.mark.django_db
def test_save_client_hq_copies_phone_and_email(staff_user):
    client = Client(**client_kwargs(phone="911111111", email="hq@example.com"))
    save_client(client, staff_user)
    hq = Site.objects.get(client=client, is_headquarters=True)
    assert hq.phone == "911111111"
    assert hq.email == "hq@example.com"
    assert hq.phone_country_id == "PT"


@pytest.mark.integration
@pytest.mark.django_db
def test_duplicate_live_nif_rejected(client, staff_user):
    client.force_login(staff_user)
    payload = {
        "kind": "person",
        "name": "First",
        "tax_number": "512345678",
        "street": "Rua A",
        "postal_code": "1000-001",
        "city": "Lisboa",
        "country_code": "PT",
        "phone": "910000001",
        "email": "first@example.com",
    }
    assert client.post(reverse("client_list"), payload).status_code == 302
    payload["name"] = "Second"
    payload["email"] = "second@example.com"
    response = client.post(reverse("client_list"), payload)
    assert response.status_code == 200
    assert b"this NIF already exists" in response.content


@pytest.mark.integration
@pytest.mark.django_db
def test_minimal_client_create(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        {
            "kind": "person",
            "name": "Quick Client",
            "tax_number": "",
            "street": "",
            "postal_code": "",
            "city": "",
            "country_code": "PT",
            "phone": "912345678",
            "email": "quick@example.com",
        },
    )
    assert response.status_code == 302
    org = Client.objects.get(name="Quick Client")
    assert org.tax_number == ""
    assert org.street == ""
    assert Site.objects.filter(client=org, is_headquarters=True).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_client_contact_fields_save_when_provided(client, staff_user, contact_positions):
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        {
            "kind": "company",
            "name": "Contact Co",
            "tax_number": "",
            "street": "",
            "postal_code": "",
            "city": "",
            "country_code": "PT",
            "phone": "912345678",
            "email": "contact@example.com",
            "contact_name": "Maria Silva",
            "contact_position": contact_positions["CEO"].pk,
        },
    )
    assert response.status_code == 302
    org = Client.objects.get(name="Contact Co")
    assert org.contact_name == "Maria Silva"
    assert org.contact_position_id == contact_positions["CEO"].pk


@pytest.mark.integration
@pytest.mark.django_db
def test_ten_digit_nif_rejected_without_save(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        {
            "kind": "person",
            "name": "Bad NIF Client",
            "tax_number": "5123456789",
            "street": "",
            "postal_code": "",
            "city": "",
            "country_code": "PT",
            "phone": "913456789",
            "email": "bad-nif@example.com",
        },
    )
    assert response.status_code == 200
    assert b"more than 9 digits" in response.content
    assert not Client.objects.filter(name="Bad NIF Client").exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_ten_digit_phone_rejected_without_save(client, staff_user):
    client.force_login(staff_user)
    response = client.post(
        reverse("client_list"),
        {
            "kind": "person",
            "name": "Bad Phone Client",
            "tax_number": "",
            "street": "",
            "postal_code": "",
            "city": "",
            "country_code": "PT",
            "phone": "9123456789",
            "email": "bad-phone@example.com",
        },
    )
    assert response.status_code == 200
    assert b"more than 9 digits" in response.content
    assert not Client.objects.filter(name="Bad Phone Client").exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_issued_quote_snapshots_client_billing(client, staff_user, site, indoor):
    from proformas.services import add_line, create_draft, issue_proforma

    proforma = create_draft(site, staff_user)
    add_line(proforma, indoor, staff_user)
    issue_proforma(proforma, staff_user)
    site.client.tax_number = "999999990"
    site.client.street = "Changed"
    site.client.save()
    client.force_login(staff_user)
    body = client.get(reverse("proforma_quote", args=[proforma.pk])).content.decode()
    assert "512345678" in body
    assert "Rua Sede 1" in body


@pytest.mark.unit
@pytest.mark.django_db
def test_site_form_rejects_hq_client_change(staff_user):
    first = Client(**client_kwargs(name="First", tax_number="501442600"))
    second = Client(**client_kwargs(name="Second", tax_number="502757191"))
    save_client(first, staff_user)
    save_client(second, staff_user)
    hq = Site.objects.get(client=first, is_headquarters=True)
    form = SiteForm(
        data={
            "client": str(second.pk),
            "alias_1": hq.alias_1,
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": hq.street,
            "postal_code": hq.postal_code,
            "city": hq.city,
            "phone": hq.phone,
            "email": hq.email,
            "contact_name": "",
            "contact_position": "",
            "notes": "",
        },
        instance=hq,
    )
    form.fields["client"].disabled = False
    assert not form.is_valid()
    assert "headquarters" in str(form.errors["client"]).lower()


@pytest.mark.integration
@pytest.mark.django_db
def test_hq_site_cannot_be_reassigned(client, staff_user):
    first = Client(**client_kwargs(name="First", tax_number="501442600"))
    second = Client(**client_kwargs(name="Second", tax_number="502757191"))
    save_client(first, staff_user)
    save_client(second, staff_user)
    hq = Site.objects.get(client=first, is_headquarters=True)
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {
            "id": str(hq.pk),
            "client": str(second.pk),
            "alias_1": hq.alias_1,
            "alias_2": "",
            "alias_3": "",
            "alias_4": "",
            "street": hq.street,
            "postal_code": hq.postal_code,
            "city": hq.city,
            "phone": hq.phone,
            "email": hq.email,
            "contact_name": "",
            "contact_position": "",
            "notes": "",
        },
    )
    assert response.status_code == 302
    hq.refresh_from_db()
    assert hq.client_id == first.pk


@pytest.mark.integration
@pytest.mark.django_db
def test_site_post_without_postal_code_rejected(client, staff_user):
    org = Client.objects.create(**client_kwargs())
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {"client": org.pk, **site_post(postal_code="")},
    )
    assert response.status_code == 200
    assert not Site.objects.filter(alias_1="Obra").exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_create_site_with_phone_and_email(client, staff_user, contact_positions):
    org = Client.objects.create(**client_kwargs())
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {
            "client": org.pk,
            **site_post(
                alias_1="Site Obra",
                phone="934567890",
                email="obra-contact@example.com",
                contact_name="Ana Costa",
                contact_position=contact_positions["Manager"].pk,
            ),
        },
    )
    assert response.status_code == 302
    site = Site.objects.get(alias_1="Site Obra")
    assert site.phone == "934567890"
    assert site.email == "obra-contact@example.com"
    assert site.contact_name == "Ana Costa"
    assert site.contact_position_id == contact_positions["Manager"].pk


@pytest.mark.integration
@pytest.mark.django_db
def test_ten_digit_site_phone_rejected_without_save(client, staff_user):
    org = Client.objects.create(**client_kwargs())
    client.force_login(staff_user)
    response = client.post(
        reverse("site_list"),
        {
            "client": org.pk,
            **site_post(alias_1="Bad Phone Site", phone="9345678901"),
        },
    )
    assert response.status_code == 200
    assert b"more than 9 digits" in response.content
    assert not Site.objects.filter(alias_1="Bad Phone Site").exists()
