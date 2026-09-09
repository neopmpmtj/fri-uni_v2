import json
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from proformas.models import ChangeLog, Item, Proforma, ProformaLine, TubingLength
from proformas.services import add_line, grouped_proforma_lines, volume_value

DEFAULT_LIMIT = 25
MAX_LIMIT = 200


def dumps(payload):
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def money(value):
    if value is None:
        return None
    return str(value)


def error_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(str(message) for message in exc.messages)
    return str(exc)


def form_error_message(form):
    parts = []
    for field, errors in form.errors.items():
        prefix = "" if field == "__all__" else f"{field}: "
        for err in errors:
            parts.append(f"{prefix}{err}")
    return " ".join(parts) or "Invalid data."


def add_pagination_arguments(parser):
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--offset", type=int, default=0)


def add_user_argument(parser):
    parser.add_argument("--user", required=True, help="Staff email (created_by)")


def parse_pagination(options):
    limit = options.get("limit", DEFAULT_LIMIT)
    offset = options.get("offset", 0)
    if limit < 1 or limit > MAX_LIMIT:
        raise CommandError(f"limit must be between 1 and {MAX_LIMIT}.")
    if offset < 0:
        raise CommandError("offset must be >= 0.")
    return limit, offset


def list_payload(entity, queryset, serialize, options):
    limit, offset = parse_pagination(options)
    page = list(queryset[offset : offset + limit])
    return {
        "ok": True,
        "entity": entity,
        "count": len(page),
        "limit": limit,
        "offset": offset,
        "items": [serialize(obj) for obj in page],
    }


def show_payload(entity, item):
    return {"ok": True, "entity": entity, "item": item}


def resolve_user(email):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist as exc:
        raise CommandError(f"Unknown user {email}") from exc
    if not user.is_active:
        raise CommandError(f"Inactive user {email}")
    return user


def live_get(model, pk, *, entity):
    try:
        return model.objects.get(pk=pk)
    except model.DoesNotExist as exc:
        raise CommandError(f"Unknown {entity} {pk}") from exc


def apply_sort(queryset, options, allowed, default):
    sort = options.get("sort") or default
    if sort not in allowed:
        raise CommandError("sort must be one of: " + ", ".join(allowed))
    return queryset.order_by(allowed[sort])


def model_form_data(instance, field_names):
    data = {}
    for name in field_names:
        field = instance._meta.get_field(name)
        if field.is_relation and not field.many_to_many:
            raw = getattr(instance, field.attname)
            data[name] = "" if raw is None else str(raw)
        else:
            value = getattr(instance, name)
            data[name] = "" if value is None else value
    return data


def overlay_options(data, options, mapping):
    for option_key, field_name in mapping.items():
        value = options.get(option_key)
        if value is not None:
            data[field_name] = value
    return data


def run_form_save(*, form_class, data, user, instance, save_fn):
    form = form_class(data, instance=instance)
    if not form.is_valid():
        raise CommandError(form_error_message(form))
    return save_fn(form.save(commit=False), user)


def is_expired(proforma):
    return (
        proforma.status == Proforma.Status.ISSUED
        and proforma.valid_until is not None
        and proforma.valid_until < timezone.localdate()
    )


def serialize_client_row(client):
    return {
        "id": client.pk,
        "label": client.name,
        "name": client.name,
        "tax_number": client.tax_number,
        "city": client.city,
        "email": client.email,
    }


def serialize_client_detail(client):
    last = (
        Proforma.objects.filter(site__client=client)
        .order_by("-created_at", "-pk")
        .first()
    )
    return {
        "id": client.pk,
        "kind": client.kind,
        "name": client.name,
        "tax_number": client.tax_number,
        "street": client.street,
        "postal_code": client.postal_code,
        "city": client.city,
        "country_code": client.country_code,
        "phone": client.phone,
        "email": client.email,
        "contact_name": client.contact_name,
        "contact_position_id": client.contact_position_id,
        "sites_count": client.sites.count(),
        "last_proforma": (
            None
            if last is None
            else {
                "id": last.pk,
                "number": last.number,
                "status": last.status,
            }
        ),
    }


def serialize_site_row(site):
    return {
        "id": site.pk,
        "label": site.alias_1,
        "alias_1": site.alias_1,
        "city": site.city,
        "client_id": site.client_id,
        "client_name": site.client.name,
    }


def serialize_site_detail(site):
    row = serialize_site_row(site)
    row.update(
        {
            "is_headquarters": site.is_headquarters,
            "alias_2": site.alias_2,
            "alias_3": site.alias_3,
            "alias_4": site.alias_4,
            "street": site.street,
            "postal_code": site.postal_code,
            "phone": site.phone,
            "email": site.email,
            "contact_name": site.contact_name,
            "contact_position_id": site.contact_position_id,
            "notes": site.notes,
        }
    )
    return row


def serialize_item_row(item):
    power = item.power
    return {
        "id": item.pk,
        "label": str(item),
        "internal_code": item.internal_code,
        "kind": item.kind,
        "power": f"{power.power} {power.unit}",
        "list_price": money(item.list_price),
        "is_default": item.is_default,
    }


def serialize_item_detail(item):
    vat = item.vat_rate
    matches = item.outdoor_matches.select_related("outdoor", "indoor")
    if item.kind == item.Kind.OUTDOOR:
        matches = item.indoor_matches.select_related("outdoor", "indoor")
    history = list(
        ChangeLog.objects.filter(
            entity_type="items", entity_id=item.pk, field="list_price"
        ).order_by("-occurred_at", "-pk")[:10]
    )
    row = serialize_item_row(item)
    row.update(
        {
            "family_id": (
                item.sub_family.family_id if item.sub_family_id else None
            ),
            "design_line_id": item.sub_family_id,
            "design_line": (
                str(item.sub_family) if item.sub_family_id else ""
            ),
            "brand_id": item.brand_id,
            "brand": item.brand.name,
            "power_id": item.power_id,
            "max_indoor_ports": item.max_indoor_ports,
            "vat_code": vat.code,
            "vat_label": vat.label,
            "vat_rate": money(vat.rate),
            "matches": [
                {
                    "id": match.pk,
                    "outdoor_id": match.outdoor_id,
                    "indoor_id": match.indoor_id,
                    "is_default": match.is_default,
                }
                for match in matches
            ],
            "price_history": [
                {
                    "old": log.old_value,
                    "new": log.new_value,
                    "reason": log.reason,
                    "occurred_at": log.occurred_at,
                }
                for log in history
            ],
        }
    )
    return row


def serialize_power_row(power):
    indoor = power.default_indoor
    return {
        "id": power.pk,
        "power": power.power,
        "unit": power.unit,
        "label": str(power),
        "volume_from_m3": money(power.volume_from_m3),
        "volume_to_m3": money(power.volume_to_m3),
        "default_indoor_id": power.default_indoor_id,
        "default_indoor_code": (
            indoor.internal_code if indoor is not None else None
        ),
    }


def serialize_proforma_row(proforma):
    site = proforma.site
    return {
        "id": proforma.pk,
        "number": proforma.number,
        "status": proforma.status,
        "client": site.client.name,
        "site": site.alias_1,
        "grand_total": money(proforma.grand_total),
        "vat_amount": money(proforma.vat_amount),
        "total_with_vat": money(proforma.total_with_vat),
        "valid_until": proforma.valid_until,
        "expired": is_expired(proforma),
    }


def serialize_proforma_line(line):
    item = line.item
    return {
        "id": line.pk,
        "parent_line_id": line.parent_line_id,
        "item_id": line.item_id,
        "label": str(item) if item is not None else line.internal_code,
        "internal_code": item.internal_code if item is not None else line.internal_code,
        "kind": item.kind if item is not None else line.kind,
        "quantity": line.quantity,
        "unit_price": money(line.unit_price),
        "tubing_amount": money(line.tubing_amount),
        "line_total": money(line.line_total),
        "vat_amount": money(line.vat_amount),
        "vat_rate": money(line.vat_rate),
    }


def serialize_proforma_detail(proforma):
    row = serialize_proforma_row(proforma)
    site = proforma.site
    client = site.client
    row.update(
        {
            "site_id": site.pk,
            "client_id": client.pk,
            "commercial_discount_percent": money(
                proforma.commercial_discount_percent
            ),
            "financial_discount_percent": money(
                proforma.financial_discount_percent
            ),
            "commercial_discount_amount": money(
                proforma.commercial_discount_amount
            ),
            "financial_discount_amount": money(
                proforma.financial_discount_amount
            ),
            "equipment_subtotal": money(proforma.equipment_subtotal),
            "tubing_total": money(proforma.tubing_total),
            "extra_labour": money(proforma.extra_labour),
            "observations": proforma.observations,
            "override_checks": proforma.override_checks,
            "validity_days": proforma.validity_days,
            "issued_at": proforma.issued_at,
            "accepted": proforma.accepted_at is not None,
            "rejected": proforma.rejected_at is not None,
            "replaces_id": proforma.replaces_id,
            "superseded_by_id": proforma.superseded_by_id,
            "client_name": proforma.client_name,
            "client_tax_number": proforma.client_tax_number,
            "site_alias_1": proforma.site_alias_1,
            "lines": [
                serialize_proforma_line(line)
                for line in grouped_proforma_lines(proforma)
            ],
        }
    )
    return row


def serialize_company(company):
    return {
        "id": company.pk,
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
        "iban": company.iban,
        "logo": bool(company.logo),
    }


def parse_volume(raw):
    try:
        return volume_value(raw)
    except ValidationError as exc:
        raise CommandError(error_message(exc)) from exc


def add_proforma_argument(parser):
    parser.add_argument("--proforma", type=int, required=True, help="Proforma id")


def parse_line_spec(spec):
    parts = spec.split(":")
    if len(parts) not in (2, 3):
        raise CommandError(
            "Each --line must be item_id:qty or item_id:qty:tubing_length_id"
        )
    try:
        item_id = int(parts[0])
        quantity = int(parts[1])
        tubing_id = int(parts[2]) if len(parts) == 3 else None
    except ValueError as exc:
        raise CommandError(
            "Each --line must be item_id:qty or item_id:qty:tubing_length_id"
        ) from exc
    item = live_get(Item, item_id, entity="item")
    tubing = None
    if tubing_id is not None:
        tubing = live_get(TubingLength, tubing_id, entity="tubing length")
    return item, quantity, tubing


def add_cli_lines(proforma, user, specs):
    current_outdoor = None
    for spec in specs:
        item, quantity, tubing = parse_line_spec(spec)
        parent = (
            current_outdoor
            if item.kind == Item.Kind.INDOOR and current_outdoor is not None
            else None
        )
        line = add_line(
            proforma,
            item,
            user,
            quantity=quantity,
            extra_tubing=tubing is not None,
            tubing_length=tubing,
            parent_line=parent,
        )
        if item.kind == Item.Kind.OUTDOOR:
            current_outdoor = line
        elif line.parent_line_id:
            current_outdoor = line.parent_line


def proforma_detail_payload(proforma):
    proforma = Proforma.objects.select_related("site__client").get(pk=proforma.pk)
    return show_payload("proforma", serialize_proforma_detail(proforma))


def require_issued(proforma):
    if proforma.status != Proforma.Status.ISSUED:
        raise CommandError("PDF is available for issued proformas only.")
    return proforma


def live_line(pk):
    return live_get(ProformaLine, pk, entity="line")


class AgentCommand(BaseCommand):
    """JSON envelope on stdout; CommandError still exits 1."""

    def handle(self, *args, **options):
        try:
            payload = self.handle_payload(*args, **options)
        except CommandError as exc:
            self.stdout.write(dumps({"ok": False, "error": str(exc)}))
            raise
        except (ValidationError, PermissionDenied) as exc:
            msg = error_message(exc)
            self.stdout.write(dumps({"ok": False, "error": msg}))
            raise CommandError(msg) from exc
        self.stdout.write(dumps(payload))

    def handle_payload(self, *args, **options):
        raise NotImplementedError
