import json
import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MaxLengthValidator
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    ActivityLog,
    ActorType,
    ChangeLog,
    Client,
    Country,
    Item,
    Parameter,
    Power,
    Proforma,
    ProformaLine,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)
from .pdf import build_proforma_pdf  # noqa: F401


def log_change(
    *,
    entity_type,
    entity_id,
    field,
    old_value,
    new_value,
    actor=None,
    actor_type=ActorType.USER,
    reason="",
):
    return ChangeLog.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        field=field,
        old_value="" if old_value is None else str(old_value),
        new_value="" if new_value is None else str(new_value),
        actor=actor,
        actor_type=actor_type,
        reason=reason or "",
        created_by=actor,
        updated_by=actor,
    )


def log_activity(
    *,
    action,
    object_type,
    object_id,
    actor=None,
    actor_type=ActorType.USER,
    details="",
):
    return ActivityLog.objects.create(
        actor=actor,
        actor_type=actor_type,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=details or "",
        created_by=actor,
        updated_by=actor,
    )


KNOWN_PARAMETER_KEYS = (
    "currency",
    "default_upfront_discount_percent",
    "tubing_length_unit",
)

_VALID_NIF_FIRST_DIGITS = set("1235689")


def normalize_postal_code(value):
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 7:
        raise ValidationError("Postal code must be 7 digits (NNNN-NNN).")
    return f"{digits[:4]}-{digits[4:]}"


def configure_nine_digit_form_field(field, *, required: bool) -> None:
    field.required = required
    field.max_length = 32
    field.validators = [
        validator
        for validator in field.validators
        if not isinstance(validator, MaxLengthValidator)
    ]
    field.widget.attrs.pop("maxlength", None)


def validate_tax_number(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 9:
        raise ValidationError("NIF has fewer than 9 digits.")
    if len(digits) > 9:
        raise ValidationError("NIF has more than 9 digits.")
    if digits[0] not in _VALID_NIF_FIRST_DIGITS:
        raise ValidationError("Invalid NIF.")
    total = sum(int(digits[i]) * (9 - i) for i in range(8))
    check = 11 - (total % 11)
    if check >= 10:
        check = 0
    if check != int(digits[8]):
        raise ValidationError("Invalid NIF check digit.")
    return digits


def validate_phone_number(value, *, country_code="PT"):
    country = Country.objects.filter(code=country_code).first()
    if country is None:
        raise ValidationError("Unknown phone country.")
    expected = country.phone_national_digits
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < expected:
        raise ValidationError(f"Phone has fewer than {expected} digits.")
    if len(digits) > expected:
        raise ValidationError(f"Phone has more than {expected} digits.")
    return digits


def get_parameter(key, default=None):
    row = Parameter.objects.filter(key=key).first()
    if row is None:
        return default
    return row.value


def update_equipment_list_price(item, new_price, *, reason, actor):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A reason is required when changing list price.")
    new_price = Decimal(str(new_price))
    old = Item.all_objects.get(pk=item.pk).list_price
    if old == new_price:
        return item
    item.list_price = new_price
    item.updated_by = actor
    item.save(update_fields=["list_price", "updated_at", "updated_by"])
    log_change(
        entity_type="items",
        entity_id=item.pk,
        field="list_price",
        old_value=old,
        new_value=new_price,
        actor=actor,
        reason=reason,
    )
    return item


def update_tubing_price(tubing, new_price, *, reason, actor):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("A reason is required when changing tubing price.")
    new_price = Decimal(str(new_price))
    old = TubingLength.all_objects.get(pk=tubing.pk).price
    if old == new_price:
        return tubing
    tubing.price = new_price
    tubing.updated_by = actor
    tubing.save(update_fields=["price", "updated_at", "updated_by"])
    log_change(
        entity_type="tubing_lengths",
        entity_id=tubing.pk,
        field="price",
        old_value=old,
        new_value=new_price,
        actor=actor,
        reason=reason,
    )
    return tubing


TWOPLACES = Decimal("0.01")


def money(value):
    try:
        return Decimal(str(value)).quantize(TWOPLACES)
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError("Enter a valid amount.") from exc


def discount_percent_value(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValidationError("Enter a valid discount percent.") from exc
    if amount < 0 or amount > 100:
        raise ValidationError("Discount percent must be between 0 and 100.")
    return amount


def labour_value(value):
    amount = money(value or 0)
    if amount < 0:
        raise ValidationError("Extra labour cannot be negative.")
    return amount


def require_draft(proforma):
    if proforma.status != Proforma.Status.DRAFT:
        raise ValidationError("Only draft proformas can be edited.")


def next_proforma_number(year=None):
    year = year or timezone.now().year
    prefix = f"PF-{year}-"
    pattern = re.compile(rf"^PF-{year}-(\d+)$")
    seqs = []
    for number in Proforma.objects.filter(number__startswith=prefix).values_list(
        "number", flat=True
    ):
        match = pattern.fullmatch(number)
        if match:
            seqs.append(int(match.group(1)))
    seq = max(seqs) + 1 if seqs else 1
    return f"{prefix}{seq:04d}"


NUMBER_ALLOCATION_ATTEMPTS = 5


def recompute_draft_totals(proforma):
    require_draft(proforma)
    lines = list(proforma.lines.select_related("tubing_length"))
    equipment = sum((line.quantity * line.unit_price for line in lines), Decimal("0.00"))
    tubing = sum((line.quantity * line.tubing_amount for line in lines), Decimal("0.00"))
    metres = Decimal("0.00")
    for line in lines:
        if line.extra_tubing and line.tubing_length_id:
            metres += Decimal(line.quantity) * line.tubing_length.length
    equipment = money(equipment)
    tubing = money(tubing)
    discount = money(equipment * proforma.upfront_discount_percent / Decimal("100"))
    grand = money(equipment - discount + tubing + proforma.extra_labour)
    proforma.equipment_subtotal = equipment
    proforma.tubing_total = tubing
    proforma.extra_tubing_metres = metres
    proforma.discount_amount = discount
    proforma.grand_total = grand
    proforma.save(
        update_fields=[
            "equipment_subtotal",
            "tubing_total",
            "extra_tubing_metres",
            "discount_amount",
            "grand_total",
            "updated_at",
        ]
    )
    return proforma


def create_draft(
    site,
    user,
    *,
    discount_percent=None,
    extra_labour=0,
    observations="",
):
    if discount_percent is None:
        discount_percent = get_parameter("default_upfront_discount_percent", "10")
    discount = discount_percent_value(discount_percent)
    labour = labour_value(extra_labour or 0)
    last_error = None
    for _ in range(NUMBER_ALLOCATION_ATTEMPTS):
        try:
            with transaction.atomic():
                proforma = Proforma(
                    site=site,
                    number=next_proforma_number(),
                    status=Proforma.Status.DRAFT,
                    upfront_discount_percent=discount,
                    extra_labour=labour,
                    observations=observations or "",
                    created_by=user,
                    updated_by=user,
                )
                proforma.save()
                recompute_draft_totals(proforma)
                log_activity(
                    action="create_proforma",
                    object_type="proforma",
                    object_id=proforma.pk,
                    actor=user,
                )
                return proforma
        except IntegrityError as exc:
            last_error = exc
    raise ValidationError("Could not allocate a unique proforma number.") from last_error


def update_draft(
    proforma,
    user,
    *,
    upfront_discount_percent=None,
    extra_labour=None,
    observations=None,
):
    require_draft(proforma)
    if upfront_discount_percent is not None:
        proforma.upfront_discount_percent = discount_percent_value(
            upfront_discount_percent
        )
    if extra_labour is not None:
        proforma.extra_labour = labour_value(extra_labour)
    if observations is not None:
        proforma.observations = observations
    proforma.updated_by = user
    proforma.save()
    return recompute_draft_totals(proforma)


def _line_money(item, quantity, extra_tubing, tubing_length):
    quantity = int(quantity)
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    unit_price = money(item.list_price)
    if extra_tubing:
        if tubing_length is None:
            raise ValidationError("Tubing length is required when extra tubing is needed.")
        tubing_amount = money(tubing_length.price)
    else:
        tubing_length = None
        tubing_amount = money(0)
    line_total = money(quantity * (unit_price + tubing_amount))
    return {
        "quantity": quantity,
        "extra_tubing": bool(extra_tubing),
        "tubing_length": tubing_length,
        "unit_price": unit_price,
        "tubing_amount": tubing_amount,
        "line_total": line_total,
    }


def add_line(proforma, item, user, *, quantity=1, extra_tubing=False, tubing_length=None):
    require_draft(proforma)
    values = _line_money(item, quantity, extra_tubing, tubing_length)
    line = ProformaLine.objects.create(
        proforma=proforma,
        item=item,
        created_by=user,
        updated_by=user,
        **values,
    )
    recompute_draft_totals(proforma)
    return line


def update_line(line, user, *, item=None, quantity=None, extra_tubing=None, tubing_length=None):
    proforma = line.proforma
    require_draft(proforma)
    item = item if item is not None else line.item
    quantity = line.quantity if quantity is None else quantity
    extra_tubing = line.extra_tubing if extra_tubing is None else extra_tubing
    if extra_tubing is False:
        tubing_length = None
    elif tubing_length is None:
        tubing_length = line.tubing_length
    values = _line_money(item, quantity, extra_tubing, tubing_length)
    for key, value in values.items():
        setattr(line, key, value)
    line.item = item
    line.updated_by = user
    line.save()
    recompute_draft_totals(proforma)
    return line


def remove_line(line, user):
    require_draft(line.proforma)
    line.soft_delete(user)
    recompute_draft_totals(line.proforma)


def require_delete_permission(user):
    if not getattr(user, "can_delete", False):
        raise PermissionDenied("Only admin can delete.")


@transaction.atomic
def save_client(client, user):
    is_new = client.pk is None
    client.updated_by = user
    if is_new:
        client.created_by = user
    client.save()
    if is_new:
        Site.objects.create(
            client=client,
            is_headquarters=True,
            alias_1=client.name,
            street=client.street,
            postal_code=client.postal_code,
            city=client.city,
            phone_country=client.phone_country,
            phone=client.phone,
            email=client.email,
            contact_name=client.contact_name,
            contact_position=client.contact_position,
            created_by=user,
            updated_by=user,
        )
    return client


def delete_client(client, user):
    require_delete_permission(user)
    for site in client.sites.all():
        if site.proformas.exists():
            raise ValidationError(
                "Cannot delete a client that has sites with proformas."
            )
    for site in client.sites.all():
        site.soft_delete(user)
    client.soft_delete(user)


def delete_site(site, user):
    require_delete_permission(user)
    if site.is_headquarters:
        raise ValidationError(
            "Cannot delete the headquarters site. Delete the client instead."
        )
    if site.proformas.exists():
        raise ValidationError("Cannot delete a site that still has proformas.")
    site.soft_delete(user)


def delete_contact_position(contact_position, user):
    require_delete_permission(user)
    if Client.objects.filter(contact_position=contact_position).exists():
        raise ValidationError("Cannot delete a position that is used by clients.")
    if Site.objects.filter(contact_position=contact_position).exists():
        raise ValidationError("Cannot delete a position that is used by sites.")
    contact_position.soft_delete(user)


def delete_family(family, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(item__sub_family__family=family).exists():
        raise ValidationError("Cannot delete a family that is used on a proforma line.")
    family.soft_delete(user)


def delete_sub_family(sub_family, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(item__sub_family=sub_family).exists():
        raise ValidationError(
            "Cannot delete a sub-family that is used on a proforma line."
        )
    sub_family.soft_delete(user)


def delete_brand(brand, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(item__brand=brand).exists():
        raise ValidationError(
            "Cannot delete a manufacturer that is used on a proforma line."
        )
    brand.soft_delete(user)


def delete_item(item, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(item=item).exists():
        raise ValidationError("Cannot delete an item that is used on a proforma line.")
    item.soft_delete(user)


def delete_vat_rate(vat_rate, user):
    require_delete_permission(user)
    if Item.objects.filter(vat_rate=vat_rate).exists():
        raise ValidationError("Cannot delete a VAT rate that is used by items.")
    vat_rate.soft_delete(user)


def delete_power(power, user):
    require_delete_permission(user)
    if Item.objects.filter(power=power).exists():
        raise ValidationError("Cannot delete a power rating that is used by items.")
    power.soft_delete(user)


def delete_tubing_length(tubing, user):
    require_delete_permission(user)
    if ProformaLine.objects.filter(tubing_length=tubing).exists():
        raise ValidationError("Cannot delete a tubing length that is used on a proforma.")
    tubing.soft_delete(user)


INTERNAL_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
VAT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def normalize_internal_code(internal_code):
    return (internal_code or "").strip().upper()


def validate_internal_code(internal_code, *, exclude_item_id=None):
    code = normalize_internal_code(internal_code)
    if not code:
        raise ValidationError("Internal code is required.")
    if INTERNAL_CODE_PATTERN.fullmatch(code) is None:
        raise ValidationError(
            "Internal code may only contain letters, digits, dots, hyphens, and underscores."
        )
    qs = Item.objects.filter(internal_code__iexact=code)
    if exclude_item_id:
        qs = qs.exclude(pk=exclude_item_id)
    if qs.exists():
        raise ValidationError(f'Internal code "{code}" is already used by another item.')
    return code


def validate_item_identity(
    *,
    sub_family,
    brand,
    kind,
    power,
    exclude_item_id=None,
):
    if not all([sub_family, brand, kind, power]):
        return
    qs = Item.objects.filter(
        sub_family=sub_family,
        brand=brand,
        kind=kind,
        power=power,
    )
    if exclude_item_id:
        qs = qs.exclude(pk=exclude_item_id)
    existing = qs.first()
    if existing:
        raise ValidationError(
            "An item with this sub-family, manufacturer, kind, and power already exists "
            f"({existing.internal_code})."
        )


def _clear_other_defaults(instance):
    if not getattr(instance, "is_default", False):
        return
    model = type(instance)
    qs = model.objects.filter(is_default=True)
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    if isinstance(instance, SubFamily):
        qs = qs.filter(family_id=instance.family_id)
    elif isinstance(instance, Item):
        qs = qs.filter(sub_family_id=instance.sub_family_id, brand_id=instance.brand_id)
    qs.update(is_default=False)


def percent_to_rate(percent):
    value = Decimal(str(percent))
    if value < 0 or value > 100:
        raise ValidationError("VAT percent must be between 0 and 100.")
    return (value / Decimal("100")).quantize(Decimal("0.0001"))


def normalize_vat_code(code):
    return (code or "").strip().upper()


def validate_vat_code(code, *, exclude_id=None):
    normalized = normalize_vat_code(code)
    if not normalized:
        raise ValidationError("VAT code is required.")
    if VAT_CODE_PATTERN.fullmatch(normalized) is None:
        raise ValidationError(
            "VAT code may only contain letters, digits, dots, hyphens, and underscores."
        )
    qs = VatRate.objects.filter(code__iexact=normalized)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError(f'VAT code "{normalized}" is already used.')
    return normalized


def normalize_power_unit(unit):
    return (unit or "").strip()


def validate_power_uniqueness(power, unit, *, exclude_id=None):
    normalized_unit = normalize_power_unit(unit)
    if not normalized_unit:
        raise ValidationError("Unit is required.")
    qs = Power.objects.filter(power=power, unit__iexact=normalized_unit)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.exists():
        raise ValidationError(f'Power "{power} {normalized_unit}" already exists.')
    return normalized_unit


@transaction.atomic
def save_audited(instance, user):
    _clear_other_defaults(instance)
    instance.updated_by = user
    if not instance.pk:
        instance.created_by = user
    instance.save()
    return instance


def save_item(item, user):
    item.internal_code = validate_internal_code(
        item.internal_code, exclude_item_id=item.pk
    )
    validate_item_identity(
        sub_family=item.sub_family,
        brand=item.brand,
        kind=item.kind,
        power=item.power,
        exclude_item_id=item.pk,
    )
    return save_audited(item, user)


def save_vat_rate(vat_rate, user):
    vat_rate.code = validate_vat_code(vat_rate.code, exclude_id=vat_rate.pk)
    return save_audited(vat_rate, user)


def save_power(power, user):
    power.unit = validate_power_uniqueness(
        power.power, power.unit, exclude_id=power.pk
    )
    return save_audited(power, user)


@transaction.atomic
def save_tubing_length(tubing, user, *, reason=""):
    new_length = tubing.length
    new_price = tubing.price
    if tubing.pk:
        original = TubingLength.all_objects.get(pk=tubing.pk)
        if original.price != new_price:
            update_tubing_price(original, new_price, reason=reason, actor=user)
            tubing.refresh_from_db()
        tubing.length = new_length
        tubing.price = new_price
    return save_audited(tubing, user)


def save_parameter(parameter, user):
    return save_audited(parameter, user)


def issue_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        require_draft(proforma)
        if not proforma.lines.exists():
            raise ValidationError("Cannot issue a proforma with no lines.")
        recompute_draft_totals(proforma)
        site = proforma.site
        client = site.client
        proforma.client_name = client.name
        proforma.client_kind = client.kind
        proforma.client_tax_number = client.tax_number
        proforma.client_street = client.street
        proforma.client_postal_code = client.postal_code
        proforma.client_city = client.city
        proforma.client_country_code = client.country_code
        proforma.client_phone = client.phone or ""
        proforma.client_email = client.email or ""
        proforma.site_alias_1 = site.alias_1
        proforma.site_alias_2 = site.alias_2 or ""
        proforma.site_alias_3 = site.alias_3 or ""
        proforma.site_alias_4 = site.alias_4 or ""
        proforma.site_street = site.street or ""
        proforma.site_postal_code = site.postal_code or ""
        proforma.site_city = site.city or ""
        proforma.site_notes = site.notes or ""
        for line in proforma.lines.select_related(
            "item__sub_family__family", "item__brand", "item__power", "tubing_length"
        ):
            line.brand_name = line.item.brand.name
            line.family_name = line.item.sub_family.family.name
            line.sub_family_name = line.item.sub_family.name
            line.internal_code = line.item.internal_code
            line.kind = line.item.kind
            line.power_value = line.item.power.power
            line.power_unit = line.item.power.unit
            line.tubing_length_value = (
                line.tubing_length.length if line.tubing_length_id else None
            )
            line.updated_by = user
            line.save()
        proforma.status = Proforma.Status.ISSUED
        proforma.updated_by = user
        proforma.save()
        log_activity(
            action="issue_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
    return proforma


def accept_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        if proforma.status != Proforma.Status.ISSUED:
            raise ValidationError("Only issued proformas can be marked accepted.")
        if proforma.superseded_by_id is not None:
            raise ValidationError("Superseded proformas cannot be marked accepted.")
        if proforma.rejected_at is not None:
            raise ValidationError("Rejected proformas cannot be marked accepted.")
        if proforma.accepted_at is not None:
            raise ValidationError("Proforma is already marked accepted.")
        proforma.accepted_at = timezone.now()
        proforma.updated_by = user
        proforma.save(update_fields=["accepted_at", "updated_at", "updated_by"])
        log_activity(
            action="accept_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
    return proforma


def unaccept_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        if proforma.status != Proforma.Status.ISSUED:
            raise ValidationError("Only issued proformas can be unmarked.")
        if proforma.accepted_at is None:
            raise ValidationError("Proforma is not marked accepted.")
        proforma.accepted_at = None
        proforma.updated_by = user
        proforma.save(update_fields=["accepted_at", "updated_at", "updated_by"])
        log_activity(
            action="unaccept_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
    return proforma


def reject_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        if proforma.status != Proforma.Status.ISSUED:
            raise ValidationError("Only issued proformas can be marked rejected.")
        if proforma.superseded_by_id is not None:
            raise ValidationError("Superseded proformas cannot be marked rejected.")
        if proforma.accepted_at is not None:
            raise ValidationError("Accepted proformas cannot be marked rejected.")
        if proforma.rejected_at is not None:
            raise ValidationError("Proforma is already marked rejected.")
        proforma.rejected_at = timezone.now()
        proforma.updated_by = user
        proforma.save(update_fields=["rejected_at", "updated_at", "updated_by"])
        log_activity(
            action="reject_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
    return proforma


def unreject_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        if proforma.status != Proforma.Status.ISSUED:
            raise ValidationError("Only issued proformas can be unmarked.")
        if proforma.rejected_at is None:
            raise ValidationError("Proforma is not marked rejected.")
        proforma.rejected_at = None
        proforma.updated_by = user
        proforma.save(update_fields=["rejected_at", "updated_at", "updated_by"])
        log_activity(
            action="unreject_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
    return proforma


def is_active_for_stats(proforma):
    return proforma.superseded_by_id is None


def change_proforma(proforma, user):
    with transaction.atomic():
        proforma = Proforma.objects.select_for_update().get(pk=proforma.pk)
        if not proforma.can_change:
            if proforma.status != Proforma.Status.ISSUED:
                raise ValidationError("Only issued proformas can be changed.")
            if proforma.accepted_at is not None:
                raise ValidationError("Accepted proformas cannot be changed.")
            if proforma.rejected_at is not None:
                raise ValidationError("Rejected proformas cannot be changed.")
            if proforma.superseded_by_id is not None:
                raise ValidationError("This proforma was already changed.")
            raise ValidationError("This proforma cannot be changed.")
        new = create_draft(
            proforma.site,
            user,
            discount_percent=proforma.upfront_discount_percent,
            extra_labour=proforma.extra_labour,
            observations=proforma.observations,
        )
        new.replaces = proforma
        new.updated_by = user
        new.save(update_fields=["replaces", "updated_at", "updated_by"])
        for line in proforma.lines.select_related("item", "tubing_length"):
            add_line(
                new,
                line.item,
                user,
                quantity=line.quantity,
                extra_tubing=line.extra_tubing,
                tubing_length=line.tubing_length,
            )
        proforma.superseded_by = new
        proforma.updated_by = user
        proforma.save(update_fields=["superseded_by", "updated_at", "updated_by"])
        log_activity(
            action="change_proforma",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
            details=json.dumps({"new_id": new.pk, "new_number": new.number}),
        )
    return new
