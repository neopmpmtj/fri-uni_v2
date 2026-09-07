from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from proformas.models import Item, ItemMatch, Power, ProformaLine
from proformas.services import add_line, create_draft, issue_proforma


@pytest.mark.unit
@pytest.mark.django_db
def test_add_indoor_auto_pairs_split_outdoor(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    indoor_line = add_line(proforma, indoor, staff_user, quantity=1)
    outdoor_line = indoor_line.parent_line
    assert outdoor_line is not None
    assert outdoor_line.item.kind == Item.Kind.OUTDOOR
    assert outdoor_line.item.max_indoor_ports == 1
    assert proforma.lines.count() == 2


@pytest.mark.unit
@pytest.mark.django_db
def test_split_outdoor_rejects_second_indoor(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    indoor_line = add_line(proforma, indoor, staff_user, quantity=1)
    with pytest.raises(ValidationError, match="only has 1 indoor port"):
        add_line(
            proforma,
            indoor,
            staff_user,
            parent_line=indoor_line.parent_line,
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_issue_requires_complete_split(staff_user, site, indoor):
    proforma = create_draft(site, staff_user)
    outdoor = indoor.outdoor_matches.get().outdoor
    add_line(proforma, outdoor, staff_user)
    with pytest.raises(ValidationError, match="exactly one indoor"):
        issue_proforma(proforma, staff_user)


@pytest.mark.unit
@pytest.mark.django_db
def test_multi_system_two_indoors(staff_user, site, indoor):
    power_12k, _ = Power.objects.get_or_create(power=12000, unit="BTU")
    second = Item.objects.create(
        sub_family=indoor.sub_family,
        brand=indoor.brand,
        vat_rate=indoor.vat_rate,
        power=power_12k,
        internal_code="MIT-SPL-I-12",
        kind=Item.Kind.INDOOR,
        list_price=Decimal("650.00"),
    )
    outdoor = Item.objects.create(
        brand=indoor.brand,
        vat_rate=indoor.vat_rate,
        power=power_12k,
        internal_code="MIT-O2-12",
        kind=Item.Kind.OUTDOOR,
        max_indoor_ports=2,
        list_price=Decimal("900.00"),
    )
    ItemMatch.objects.create(outdoor=outdoor, indoor=indoor, is_default=False)
    ItemMatch.objects.create(outdoor=outdoor, indoor=second, is_default=False)
    proforma = create_draft(site, staff_user, discount_percent=0)
    parent = add_line(proforma, outdoor, staff_user)
    add_line(proforma, indoor, staff_user, parent_line=parent)
    add_line(proforma, second, staff_user, parent_line=parent)
    issued = issue_proforma(proforma, staff_user)
    assert issued.lines.filter(parent_line__isnull=True).count() == 1
    assert issued.lines.filter(parent_line__isnull=False).count() == 2


@pytest.mark.integration
@pytest.mark.django_db
def test_edit_split_outdoor_line_preselects_item(client, staff_user, site, indoor):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    indoor_line = add_line(proforma, indoor, staff_user, quantity=1)
    outdoor_line = indoor_line.parent_line
    response = client.get(
        reverse("proforma_detail", args=[proforma.pk]),
        {"line": str(outdoor_line.pk)},
    )
    assert response.status_code == 200
    assert response.context["outdoor_only"] is True
    form = response.context["line_form"]
    assert outdoor_line.item in form.fields["item"].queryset
    assert form["item"].value() == outdoor_line.item.pk
    html = response.content.decode()
    assert 'id="id_sub_family"' not in html
    assert 'name="id_sub_family"' not in html
    assert f'value="{outdoor_line.item.pk}"' in html
    assert "formnovalidate" in html


@pytest.mark.integration
@pytest.mark.django_db
def test_delete_split_outdoor_line_without_item_posted(
    client, staff_user, site, indoor
):
    client.force_login(staff_user)
    proforma = create_draft(site, staff_user)
    indoor_line = add_line(proforma, indoor, staff_user, quantity=1)
    outdoor_line = indoor_line.parent_line
    response = client.post(
        reverse("proforma_detail", args=[proforma.pk]),
        {
            "action": "delete_line",
            "id": str(outdoor_line.pk),
            "item": "",
        },
    )
    assert response.status_code == 302
    assert not ProformaLine.objects.filter(pk=outdoor_line.pk).exists()
    assert not ProformaLine.objects.filter(pk=indoor_line.pk).exists()
