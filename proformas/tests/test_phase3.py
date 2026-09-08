from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from proformas.models import (
    Brand,
    ChangeLog,
    Family,
    Item,
    ItemMatch,
    Parameter,
    Power,
    SubFamily,
    TubingLength,
    VatRate,
)
from proformas.seed import FAMILY_AC
from proformas.services import (
    normalize_internal_code,
    percent_to_rate,
    update_equipment_list_price,
    validate_internal_code,
    validate_item_identity,
)


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="admin@example.com",
        password="pass12345",
        role=User.Role.ADMIN,
    )


@pytest.mark.unit
@pytest.mark.django_db
def test_migrate_seeds_parameters_family_brands_and_tubing():
    assert Parameter.objects.get(key="currency").value == "EUR"
    assert Parameter.objects.get(key="default_financial_discount_percent").value == "10"
    assert Parameter.objects.get(key="default_commercial_discount_percent").value == "0"
    assert Parameter.objects.get(key="tubing_length_unit").value == "m"
    ac = Family.objects.get(name=FAMILY_AC)
    assert ac.is_default
    assert Family.objects.count() == 1
    assert set(
        Brand.objects.filter(
            name__in=["Mitsubishi", "LG", "Nippon", "Daikin"]
        ).values_list("name", flat=True)
    ) == {"Mitsubishi", "LG", "Nippon", "Daikin"}
    assert Item.objects.count() == 0
    assert set(TubingLength.objects.values_list("length", "price")) == {
        (Decimal("3.00"), Decimal("25.00")),
        (Decimal("5.00"), Decimal("40.00")),
        (Decimal("10.00"), Decimal("70.00")),
    }


@pytest.mark.unit
@pytest.mark.django_db
def test_internal_code_is_stored_uppercase():
    assert normalize_internal_code(" dai-sen-i-9 ") == "DAI-SEN-I-9"


@pytest.mark.unit
@pytest.mark.django_db
def test_internal_code_unique_is_case_insensitive(indoor):
    with pytest.raises(ValidationError):
        validate_internal_code("mit-spl-i-9")


@pytest.mark.unit
@pytest.mark.django_db
def test_item_identity_unique_rejects_duplicate_combo(indoor):
    with pytest.raises(ValidationError) as exc:
        validate_item_identity(
            sub_family=indoor.sub_family,
            brand=indoor.brand,
            kind=indoor.kind,
            power=indoor.power,
        )
    assert "MIT-SPL-I-9" in str(exc.value)


@pytest.mark.unit
@pytest.mark.django_db
def test_item_identity_unique_allows_same_item_on_edit(indoor):
    validate_item_identity(
        sub_family=indoor.sub_family,
        brand=indoor.brand,
        kind=indoor.kind,
        power=indoor.power,
        exclude_item_id=indoor.pk,
    )


@pytest.mark.integration
@pytest.mark.django_db
def test_new_item_rejects_duplicate_identity(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": indoor.sub_family_id,
            "brand": indoor.brand_id,
            "vat_rate": indoor.vat_rate_id,
            "power": indoor.power_id,
            "internal_code": "ABC-TESTE",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 200
    assert Item.objects.filter(internal_code="ABC-TESTE").count() == 0
    assert "MIT-SPL-I-9" in str(response.context["form"].non_field_errors())


@pytest.mark.integration
@pytest.mark.django_db
def test_edit_item_same_identity_succeeds(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": indoor.sub_family_id,
            "brand": indoor.brand_id,
            "vat_rate": indoor.vat_rate_id,
            "power": indoor.power_id,
            "internal_code": "MIT-SPL-I-9",
            "kind": Item.Kind.INDOOR,
            "is_default": "on",
            "action": "save",
            "id": indoor.pk,
        },
    )
    assert response.status_code == 302
    indoor.refresh_from_db()
    assert indoor.is_default


@pytest.mark.integration
@pytest.mark.django_db
def test_edit_item_rejects_duplicate_identity(client, staff_user, indoor):
    client.force_login(staff_user)
    power_12k, _ = Power.objects.get_or_create(power=12000, unit="BTU")
    other = Item.objects.create(
        sub_family=indoor.sub_family,
        brand=indoor.brand,
        vat_rate=indoor.vat_rate,
        power=power_12k,
        internal_code="MIT-SPL-I-12",
        kind=Item.Kind.INDOOR,
        list_price=Decimal("600.00"),
    )
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": other.sub_family_id,
            "brand": other.brand_id,
            "vat_rate": other.vat_rate_id,
            "power": other.power_id,
            "internal_code": indoor.internal_code,
            "kind": other.kind,
            "action": "save",
            "id": indoor.pk,
        },
    )
    assert response.status_code == 200
    original_power_id = indoor.power_id
    indoor.refresh_from_db()
    assert indoor.power_id == original_power_id
    assert "MIT-SPL-I-12" in str(response.context["form"].non_field_errors())


@pytest.mark.integration
@pytest.mark.django_db
def test_same_sub_family_different_manufacturer_allowed(client, staff_user, indoor):
    client.force_login(staff_user)
    lg, _ = Brand.objects.get_or_create(name="LG")
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": indoor.sub_family_id,
            "brand": lg.pk,
            "vat_rate": indoor.vat_rate_id,
            "power": indoor.power_id,
            "internal_code": "LG-SPL-I-9",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 302
    assert Item.objects.filter(internal_code="LG-SPL-I-9").exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_item_list_sorts_by_manufacturer_desc(client, staff_user, indoor):
    client.force_login(staff_user)
    lg, _ = Brand.objects.get_or_create(name="LG")
    Item.objects.create(
        sub_family=indoor.sub_family,
        brand=lg,
        vat_rate=indoor.vat_rate,
        power=indoor.power,
        internal_code="LG-SPL-I-9",
        kind=Item.Kind.INDOOR,
        list_price=Decimal("500.00"),
    )
    response = client.get(
        reverse("item_list"),
        {"sort": "manufacturer", "dir": "desc"},
    )
    assert response.status_code == 200
    codes = [row.internal_code for row in response.context["items"]]
    assert codes.index("MIT-SPL-I-9") < codes.index("LG-SPL-I-9")


@pytest.mark.unit
@pytest.mark.django_db
def test_list_price_without_reason_fails(indoor, admin_user):
    with pytest.raises(ValidationError):
        update_equipment_list_price(
            indoor, Decimal("510.00"), reason="", actor=admin_user
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_list_price_with_reason_writes_change_log(indoor, admin_user):
    update_equipment_list_price(
        indoor, Decimal("510.00"), reason="supplier increase", actor=admin_user
    )
    log = ChangeLog.objects.get(field="list_price")
    assert log.reason == "supplier increase"
    assert log.entity_type == "items"
    assert log.new_value == "510.00"
    indoor.refresh_from_db()
    assert indoor.list_price == Decimal("510.00")


@pytest.mark.integration
@pytest.mark.django_db
def test_seed_catalog_twice_does_not_duplicate():
    call_command("seed_catalog")
    call_command("seed_catalog")
    assert Brand.objects.filter(name="Mitsubishi").count() == 1
    assert Brand.objects.filter(
        name__in=["Mitsubishi", "LG", "Nippon", "Daikin"]
    ).count() == 4
    ac = Family.objects.get(name=FAMILY_AC)
    assert ac.is_default
    names = set(
        SubFamily.objects.filter(family=ac).values_list("name", flat=True)
    )
    assert names == {
        "Split",
        "Sensira",
        "Comfora",
        "Perfera",
        "Perfera Floor",
        "Stylish",
        "Emura",
        "Ururu Sarara",
    }
    daikin_sensira = Item.objects.filter(
        brand__name="Daikin", sub_family__name="Sensira"
    )
    assert daikin_sensira.count() == 3
    indoor_9 = Item.objects.get(
        brand__name="Daikin",
        sub_family__name="Sensira",
        kind=Item.Kind.INDOOR,
        power__power=9000,
        power__unit="BTU",
    )
    assert indoor_9.internal_code == "DAI-SEN-I-9"
    assert indoor_9.vat_rate.code == "VAT23"
    power_9 = Power.objects.get(power=9000, unit="BTU")
    assert power_9.volume_from_m3 == Decimal("0")
    assert power_9.volume_to_m3 == Decimal("20")
    assert power_9.default_indoor.internal_code == "DAI-PRF-I-9"
    split_outdoor = Item.objects.get(internal_code="DAI-O1-9")
    assert split_outdoor.kind == Item.Kind.OUTDOOR
    assert split_outdoor.sub_family_id is None
    assert split_outdoor.max_indoor_ports == 1
    assert ItemMatch.objects.filter(
        outdoor=split_outdoor, indoor=indoor_9, is_default=True
    ).exists()
    multi = Item.objects.get(internal_code="DAI-O2-18")
    assert multi.max_indoor_ports == 2
    assert Family.objects.filter(name=FAMILY_AC).count() == 1
    assert Family.objects.count() == 1
    assert VatRate.objects.filter(is_default=True).count() == 1
    assert VatRate.objects.get(code="VAT23").rate == Decimal("0.2300")
    split = SubFamily.objects.get(name="Split", family=ac)
    perfera = SubFamily.objects.get(name="Perfera", family=ac)
    assert split.brand_id is None
    assert perfera.brand.name == "Daikin"
    assert Power.objects.filter(unit="BTU").count() == 3


@pytest.mark.integration
@pytest.mark.django_db
def test_sub_family_is_shared_across_brands():
    call_command("seed_catalog")
    split = SubFamily.objects.get(name="Split", family__name=FAMILY_AC)
    assert split.brand_id is None
    assert Item.objects.filter(sub_family=split, brand__name="Mitsubishi").exists()
    assert Item.objects.filter(sub_family=split, brand__name="LG").exists()
    assert not Item.objects.filter(
        sub_family=split, brand__name="Daikin"
    ).exists()
    assert not Item.objects.filter(sub_family=split, kind=Item.Kind.OUTDOOR).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_can_open_catalog_pages(client, staff_user):
    client.force_login(staff_user)
    for name in (
        "item_list",
        "family_list",
        "sub_family_list",
        "manufacturer_list",
        "vat_rate_list",
        "power_list",
        "parameter_list",
        "tubing_length_list",
        "contact_position_list",
    ):
        response = client.get(reverse(name))
        assert response.status_code == 200
    dashboard = client.get("/")
    assert b'data-i18n="items"' in dashboard.content
    assert b'data-i18n="families"' in dashboard.content
    assert b'data-i18n="vatRates"' in dashboard.content
    assert b'data-i18n="powers"' in dashboard.content
    assert b'data-i18n="parameters"' in dashboard.content
    assert b'data-i18n="tubingLengths"' in dashboard.content
    assert b'data-i18n="contactPositions"' in dashboard.content
    assert b"catalogAdmin" not in dashboard.content


@pytest.mark.unit
def test_percent_to_rate_stores_fraction():
    assert percent_to_rate("23") == Decimal("0.2300")


@pytest.mark.integration
@pytest.mark.django_db
def test_new_item_form_preselects_default_vat(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.get(reverse("item_list"), {"new": "1"})
    assert response.status_code == 200
    assert response.context["form"].fields["vat_rate"].initial == indoor.vat_rate_id


@pytest.mark.integration
@pytest.mark.django_db
def test_new_item_sub_family_options_include_manufacturer_data(client, staff_user):
    call_command("seed_catalog")
    client.force_login(staff_user)
    response = client.get(reverse("item_list"), {"new": "1"})
    html = str(response.context["form"]["sub_family"])
    perfera = SubFamily.objects.get(name="Perfera", family__name=FAMILY_AC)
    daikin = Brand.objects.get(name="Daikin")
    split = SubFamily.objects.get(name="Split", family__name=FAMILY_AC)
    assert f'data-brand="{daikin.pk}"' in html
    assert f'value="{perfera.pk}"' in html
    split_tag = html.split(f'value="{split.pk}"', 1)[1].split("</option>", 1)[0]
    assert "data-brand=" not in split_tag


@pytest.mark.integration
@pytest.mark.django_db
def test_item_post_without_power_is_invalid(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": indoor.sub_family_id,
            "brand": indoor.brand_id,
            "vat_rate": indoor.vat_rate_id,
            "internal_code": "NEW-I-9",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 200
    assert Item.objects.filter(internal_code="NEW-I-9").count() == 0
    assert response.context["form"].errors.get("power")


@pytest.mark.integration
@pytest.mark.django_db
def test_item_post_without_vat_rate_is_invalid(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": indoor.sub_family_id,
            "brand": indoor.brand_id,
            "power": indoor.power_id,
            "internal_code": "NEW-I-9",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 200
    assert Item.objects.filter(internal_code="NEW-I-9").count() == 0
    assert response.context["form"].errors.get("vat_rate")


@pytest.mark.integration
@pytest.mark.django_db
def test_new_item_inherits_sub_family_manufacturer(client, staff_user):
    call_command("seed_catalog")
    client.force_login(staff_user)
    ac = Family.objects.get(name=FAMILY_AC)
    daikin = Brand.objects.get(name="Daikin")
    mitsu = Brand.objects.get(name="Mitsubishi")
    owned_range = SubFamily.objects.create(
        family=ac, name="Owned Range", brand=daikin
    )
    vat = VatRate.objects.get(code="VAT23")
    power = Power.objects.get(power=9000, unit="BTU")
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": owned_range.pk,
            "brand": mitsu.pk,
            "vat_rate": vat.pk,
            "power": power.pk,
            "internal_code": "DAI-OWN-I-9",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 302
    item = Item.objects.get(internal_code="DAI-OWN-I-9")
    assert item.brand_id == daikin.pk


@pytest.mark.integration
@pytest.mark.django_db
def test_new_item_split_without_manufacturer_is_invalid(client, staff_user):
    call_command("seed_catalog")
    client.force_login(staff_user)
    split = SubFamily.objects.get(name="Split", family__name=FAMILY_AC)
    vat = VatRate.objects.get(code="VAT23")
    power = Power.objects.get(power=9000, unit="BTU")
    response = client.post(
        reverse("item_list"),
        {
            "sub_family": split.pk,
            "vat_rate": vat.pk,
            "power": power.pk,
            "internal_code": "NEW-SPL-I-9",
            "kind": Item.Kind.INDOOR,
            "action": "save",
        },
    )
    assert response.status_code == 200
    assert Item.objects.filter(internal_code="NEW-SPL-I-9").count() == 0
    assert response.context["form"].errors.get("brand")


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_can_save_sub_family_with_and_without_manufacturer(
    client, staff_user, indoor
):
    client.force_login(staff_user)
    family = indoor.sub_family.family
    brand = indoor.brand
    blank = client.post(
        reverse("sub_family_list"),
        {
            "family": family.pk,
            "name": "Shared Range",
            "action": "save",
        },
    )
    assert blank.status_code == 302
    shared = SubFamily.objects.get(name="Shared Range", family=family)
    assert shared.brand_id is None
    owned = client.post(
        reverse("sub_family_list"),
        {
            "family": family.pk,
            "name": "Owned Range",
            "brand": brand.pk,
            "action": "save",
        },
    )
    assert owned.status_code == 302
    row = SubFamily.objects.get(name="Owned Range", family=family)
    assert row.brand_id == brand.pk


@pytest.mark.integration
@pytest.mark.django_db
def test_staff_cannot_delete_vat_rate(client, staff_user, indoor):
    client.force_login(staff_user)
    response = client.post(
        reverse("vat_rate_list"),
        {"id": str(indoor.vat_rate_id), "action": "delete"},
    )
    assert response.status_code == 302
    follow = client.get(response.url)
    assert b"Only admin can delete" in follow.content
    assert VatRate.objects.filter(pk=indoor.vat_rate_id).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_tubing_price_change_without_reason_fails(client, staff_user, tubing):
    client.force_login(staff_user)
    response = client.post(
        reverse("tubing_length_list"),
        {
            "id": str(tubing.pk),
            "length": str(tubing.length),
            "price": "99.00",
            "reason": "",
            "action": "save",
        },
    )
    assert response.status_code == 200
    tubing.refresh_from_db()
    assert tubing.price == Decimal("40.00")
    assert response.context["form"].errors.get("reason")
