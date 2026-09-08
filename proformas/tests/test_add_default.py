from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from proformas.models import Item, Power, ProformaLine
from proformas.services import (
    add_default_split,
    create_draft,
    power_for_volume,
    save_power,
)


def _set_band(power, volume_from, volume_to, indoor=None):
    power.volume_from_m3 = Decimal(str(volume_from))
    power.volume_to_m3 = Decimal(str(volume_to))
    if indoor is not None:
        power.default_indoor = indoor
    power.save()
    return power


@pytest.mark.unit
@pytest.mark.django_db
def test_power_for_volume_picks_inclusive_bands(indoor):
    power_9 = indoor.power
    _set_band(power_9, 0, 20, indoor)
    power_12, _ = Power.objects.get_or_create(power=12000, unit="BTU")
    _set_band(power_12, 21, 35)
    power_18, _ = Power.objects.get_or_create(power=18000, unit="BTU")
    _set_band(power_18, 36, 50)

    assert power_for_volume(0).pk == power_9.pk
    assert power_for_volume(20).pk == power_9.pk
    assert power_for_volume(21).pk == power_12.pk
    assert power_for_volume(50).pk == power_18.pk
    with pytest.raises(ValidationError, match="No power rating covers"):
        power_for_volume(51)


@pytest.mark.unit
@pytest.mark.django_db
def test_save_power_rejects_overlapping_bands(indoor):
    _set_band(indoor.power, 0, 20)
    other, _ = Power.objects.get_or_create(power=12000, unit="BTU")
    other.volume_from_m3 = Decimal("20")
    other.volume_to_m3 = Decimal("35")
    with pytest.raises(ValidationError, match="overlaps"):
        save_power(other, None)


@pytest.mark.unit
@pytest.mark.django_db
def test_add_default_split_inserts_matched_pair(staff_user, site, indoor):
    _set_band(indoor.power, 0, 20, indoor)
    proforma = create_draft(site, staff_user)
    indoor_line = add_default_split(proforma, Decimal("15"), staff_user)
    assert indoor_line.item_id == indoor.pk
    assert indoor_line.quantity == 1
    assert indoor_line.extra_tubing is False
    outdoor_line = indoor_line.parent_line
    assert outdoor_line is not None
    assert outdoor_line.item.kind == Item.Kind.OUTDOOR
    assert outdoor_line.item.max_indoor_ports == 1
    assert proforma.lines.count() == 2


@pytest.mark.unit
@pytest.mark.django_db
def test_add_default_split_requires_default_indoor(staff_user, site, indoor):
    _set_band(indoor.power, 0, 20, indoor=None)
    indoor.power.default_indoor = None
    indoor.power.save(update_fields=["default_indoor"])
    proforma = create_draft(site, staff_user)
    with pytest.raises(ValidationError, match="no default indoor"):
        add_default_split(proforma, Decimal("10"), staff_user)


@pytest.mark.integration
@pytest.mark.django_db
def test_add_default_from_draft_page(client, staff_user, site, indoor):
    _set_band(indoor.power, 0, 20, indoor)
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    response = client.post(
        reverse("proforma_detail", kwargs={"pk": proforma.pk}),
        {"action": "add_default", "volume_m3": "12"},
    )
    assert response.status_code == 302
    assert ProformaLine.objects.filter(proforma=proforma, item=indoor).exists()
    outdoor = indoor.outdoor_matches.get().outdoor
    assert ProformaLine.objects.filter(proforma=proforma, item=outdoor).exists()


@pytest.mark.integration
@pytest.mark.django_db
def test_draft_page_has_add_default_button(client, staff_user, site):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    html = client.get(reverse("proforma_detail", kwargs={"pk": proforma.pk})).content.decode()
    assert 'data-i18n="addDefault"' in html
    assert "new_line=default" in html
