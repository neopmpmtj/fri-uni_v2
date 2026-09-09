from decimal import Decimal

from decouple import config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError

from accounts.models import User
from proformas.models import (
    Brand,
    Client,
    ContactPosition,
    Family,
    Item,
    ItemMatch,
    Parameter,
    Power,
    Proforma,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)
from proformas.services import (
    add_line,
    accept_proforma,
    reject_proforma,
    change_proforma,
    create_draft,
    issue_proforma,
)


SIMPLE_BRANDS = ("Mitsubishi", "LG", "Nippon")
SIMPLE_SUBFAMILY = "Split"
BTUS = (9000, 12000, 18000)
INDOOR_PRICES = {9000: "500.00", 12000: "650.00", 18000: "800.00"}

FAMILY_AC = "Air conditioners"

DESIGN_LINES = (
    "Split",
    "Sensira",
    "Comfora",
    "Perfera",
    "Perfera Floor",
    "Stylish",
    "Emura",
    "Ururu Sarara",
)

# Named indoor design lines from Daikin PT air-to-air heat pumps:
# https://www.daikin.pt/pt_pt/particular/products-and-advice/product-categories/heat-pumps/air-to-air-heat-pumps.html
DAIKIN_DESIGN_LINES = (
    "Sensira",
    "Comfora",
    "Perfera",
    "Perfera Floor",
    "Stylish",
    "Emura",
    "Ururu Sarara",
)
DAIKIN_INDOOR = {
    "Sensira": {9000: "450.00", 12000: "580.00", 18000: "720.00"},
    "Comfora": {9000: "480.00", 12000: "620.00", 18000: "760.00"},
    "Perfera": {9000: "550.00", 12000: "700.00", 18000: "860.00"},
    "Perfera Floor": {9000: "580.00", 12000: "740.00", 18000: "920.00"},
    "Stylish": {9000: "620.00", 12000: "780.00", 18000: "960.00"},
    "Emura": {9000: "680.00", 12000: "860.00", 18000: "1050.00"},
    "Ururu Sarara": {9000: "750.00", 12000: "950.00", 18000: "1200.00"},
}
SPLIT_OUTDOOR_PRICES = {
    "Mitsubishi": {9000: "550.00", 12000: "700.00", 18000: "900.00"},
    "LG": {9000: "550.00", 12000: "700.00", 18000: "900.00"},
    "Nippon": {9000: "550.00", 12000: "700.00", 18000: "900.00"},
    "Daikin": {9000: "500.00", 12000: "630.00", 18000: "780.00"},
}
DAIKIN_MULTI_OUTDOOR_PRICE = "1400.00"

BRAND_CODE = {
    "Mitsubishi": "MIT",
    "LG": "LG",
    "Nippon": "NIP",
    "Daikin": "DAI",
}
SUBFAMILY_CODE = {
    "Split": "SPL",
    "Sensira": "SEN",
    "Comfora": "COM",
    "Perfera": "PRF",
    "Perfera Floor": "PRFF",
    "Stylish": "STY",
    "Emura": "EMU",
    "Ururu Sarara": "URU",
}

TUBING = (("3.00", "25.00"), ("5.00", "40.00"), ("10.00", "70.00"))
PARAMETERS = (
    ("currency", "EUR"),
    ("default_financial_discount_percent", "10"),
    ("default_commercial_discount_percent", "0"),
    ("default_validity_days", "7"),
    ("tubing_length_unit", "m"),
)
VAT_RATES = (
    ("VAT23", "23%", "0.2300", True),
    ("VAT13", "13%", "0.1300", False),
    ("VAT6", "6%", "0.0600", False),
    ("VAT_EXEMPT", "Exempt", "0.0000", False),
)

DEMO_ADMIN_EMAIL = "proforma-admin@fribila.dev"
DEMO_MANAGER_EMAIL = "proforma-manager@fribila.dev"
DEMO_PASSWORD = "fribila-demo"
AGENT_EMAIL = "agent@fribila.dev"
AGENT_ADMIN_EMAIL = "agent-admin@fribila.dev"
AGENT_PASSWORD_ENV = "AGENT_PASSWORD"
AGENT_ADMIN_PASSWORD_ENV = "AGENT_ADMIN_PASSWORD"

CONTACT_POSITIONS = ("CEO", "CFO", "Manager", "Director", "Other")

DEMO_CLIENTS = (
    {
        "kind": "company",
        "name": "Construtora Atlantico, Lda.",
        "tax_number": "501442600",
        "street": "Avenida da Liberdade 100",
        "postal_code": "1250-140",
        "city": "Lisboa",
        "country_code": "PT",
        "phone": "210001100",
        "email": "obras@atlantico.example",
        "contact_name": "João Pereira",
        "contact_position": "CEO",
        "sites": (
            {
                "alias_1": "Moradia Cascais",
                "alias_2": "Casa principal",
                "street": "Rua da Palmeira 12",
                "postal_code": "2750-123",
                "city": "Cascais",
                "notes": "Moradia unifamiliar, wall-mounted indoor units.",
            },
            {
                "alias_1": "Bloco Oeiras",
                "alias_2": "Entrada B",
                "street": "Avenida da Republica 80",
                "postal_code": "2780-010",
                "city": "Oeiras",
                "notes": "Apartments under construction.",
            },
        ),
    },
    {
        "kind": "company",
        "name": "Residencias do Tejo, Lda.",
        "tax_number": "502757191",
        "street": "Rua do Ouro 50",
        "postal_code": "1100-060",
        "city": "Lisboa",
        "country_code": "PT",
        "phone": "210002200",
        "email": "obras@tejo.example",
        "sites": (
            {
                "alias_1": "Apartamento Alfama",
                "street": "Rua de Sao Pedro 4",
                "postal_code": "1100-334",
                "city": "Lisboa",
                "notes": "Refurbishment, low ceilings.",
            },
        ),
    },
    {
        "kind": "company",
        "name": "Hotel Brisa Azul",
        "tax_number": "506848558",
        "street": "Praca da Liberdade 50",
        "postal_code": "4000-322",
        "city": "Porto",
        "country_code": "PT",
        "phone": "220003300",
        "email": "manutencao@brisaazul.example",
        "sites": (
            {
                "alias_1": "Ala Norte",
                "alias_2": "Quartos 101-120",
                "street": "Avenida do Brasil 200",
                "postal_code": "4100-100",
                "city": "Porto",
            },
            {
                "alias_1": "Spa",
                "street": "Avenida do Brasil 200",
                "postal_code": "4100-100",
                "city": "Porto",
                "notes": "Wet area, floor-standing unit.",
            },
            {
                "alias_1": "Receção",
                "alias_2": "Lobby",
                "street": "Avenida do Brasil 200",
                "postal_code": "4100-100",
                "city": "Porto",
                "notes": "Issued quote awaiting client decision — use to test Change.",
            },
        ),
    },
)


VOLUME_BANDS = {
    9000: (Decimal("0"), Decimal("20")),
    12000: (Decimal("21"), Decimal("35")),
    18000: (Decimal("36"), Decimal("50")),
}


def _live_get_or_create(model, defaults=None, **lookup):
    obj = model.objects.filter(**lookup).first()
    if obj:
        return obj, False
    data = dict(lookup)
    if defaults:
        data.update(defaults)
    return model.objects.create(**data), True


def _indoor_code(brand_name, design_line_name, power_amount):
    brand = BRAND_CODE.get(brand_name, brand_name[:3].upper())
    sub = SUBFAMILY_CODE.get(design_line_name, design_line_name[:3].upper())
    return f"{brand}-{sub}-I-{int(power_amount) // 1000}"


def _outdoor_code(brand_name, ports, power_amount):
    brand = BRAND_CODE.get(brand_name, brand_name[:3].upper())
    return f"{brand}-O{ports}-{int(power_amount) // 1000}"


def _seed_powers():
    by_amount = {}
    for amount in BTUS:
        vol_from, vol_to = VOLUME_BANDS[amount]
        row, created = _live_get_or_create(
            Power,
            defaults={
                "volume_from_m3": vol_from,
                "volume_to_m3": vol_to,
            },
            power=amount,
            unit="BTU",
        )
        if not created and (
            row.volume_from_m3 != vol_from or row.volume_to_m3 != vol_to
        ):
            row.volume_from_m3 = vol_from
            row.volume_to_m3 = vol_to
            row.save(update_fields=["volume_from_m3", "volume_to_m3"])
        by_amount[amount] = row
    return by_amount


def _seed_power_defaults(powers_by_amount):
    for amount in BTUS:
        power = powers_by_amount[amount]
        indoor = Item.objects.filter(
            brand__name="Daikin",
            sub_family__name="Perfera",
            kind=Item.Kind.INDOOR,
            power=power,
        ).first()
        if indoor is None:
            continue
        if power.default_indoor_id != indoor.pk:
            power.default_indoor = indoor
            power.save(update_fields=["default_indoor"])


def _seed_indoor_items(brand, design_line, prices, vat_rate, powers_by_amount):
    items = []
    for amount in BTUS:
        power = powers_by_amount[amount]
        indoor_defaults = {
            "list_price": Decimal(prices[amount]),
            "internal_code": _indoor_code(brand.name, design_line.name, amount),
            "vat_rate": vat_rate,
            "power": power,
            "max_indoor_ports": None,
        }
        item, _ = _live_get_or_create(
            Item,
            defaults=indoor_defaults,
            brand=brand,
            sub_family=design_line,
            kind=Item.Kind.INDOOR,
            power=power,
        )
        items.append(item)
    return items


def _seed_split_outdoors(brand, vat_rate, powers_by_amount):
    prices = SPLIT_OUTDOOR_PRICES[brand.name]
    outdoors = {}
    for amount in BTUS:
        power = powers_by_amount[amount]
        item, _ = _live_get_or_create(
            Item,
            defaults={
                "list_price": Decimal(prices[amount]),
                "internal_code": _outdoor_code(brand.name, 1, amount),
                "vat_rate": vat_rate,
                "power": power,
                "sub_family": None,
            },
            brand=brand,
            kind=Item.Kind.OUTDOOR,
            power=power,
            max_indoor_ports=1,
        )
        outdoors[amount] = item
    return outdoors


def _seed_match(outdoor, indoor, *, is_default=False):
    _live_get_or_create(
        ItemMatch,
        defaults={"is_default": is_default},
        outdoor=outdoor,
        indoor=indoor,
    )


def _seed_contact_positions():
    for name in CONTACT_POSITIONS:
        _live_get_or_create(ContactPosition, name=name)


def _resolve_contact_position(value):
    if not value:
        return None
    if isinstance(value, ContactPosition):
        return value
    return ContactPosition.objects.filter(name__iexact=value).first()


def seed_catalog():
    vat23 = None
    for code, label, rate, is_default in VAT_RATES:
        vat, _ = _live_get_or_create(
            VatRate,
            defaults={
                "label": label,
                "rate": Decimal(rate),
                "is_default": is_default,
            },
            code=code,
        )
        if code == "VAT23":
            vat23 = vat

    powers_by_amount = _seed_powers()

    ac, _ = _live_get_or_create(Family, defaults={"is_default": True}, name=FAMILY_AC)

    daikin, _ = _live_get_or_create(Brand, name="Daikin")
    sub_by_name = {}
    for name in DESIGN_LINES:
        defaults = {"is_default": name == SIMPLE_SUBFAMILY}
        if name in DAIKIN_DESIGN_LINES:
            defaults["brand"] = daikin
        sub, created = _live_get_or_create(
            SubFamily, defaults=defaults, family=ac, name=name
        )
        if (
            not created
            and name in DAIKIN_DESIGN_LINES
            and sub.brand_id != daikin.pk
        ):
            sub.brand = daikin
            sub.save(update_fields=["brand"])
        sub_by_name[name] = sub

    all_indoors = []
    split_outdoors = {}
    for name in SIMPLE_BRANDS:
        brand, _ = _live_get_or_create(Brand, name=name)
        indoors = _seed_indoor_items(
            brand,
            sub_by_name[SIMPLE_SUBFAMILY],
            INDOOR_PRICES,
            vat23,
            powers_by_amount,
        )
        all_indoors.extend(indoors)
        split_outdoors[brand.name] = _seed_split_outdoors(
            brand, vat23, powers_by_amount
        )

    daikin_indoors = []
    for sub_name in DAIKIN_DESIGN_LINES:
        indoors = _seed_indoor_items(
            daikin,
            sub_by_name[sub_name],
            DAIKIN_INDOOR[sub_name],
            vat23,
            powers_by_amount,
        )
        daikin_indoors.extend(indoors)
        all_indoors.extend(indoors)
    split_outdoors["Daikin"] = _seed_split_outdoors(
        daikin, vat23, powers_by_amount
    )

    for indoor in all_indoors:
        outdoor = split_outdoors[indoor.brand.name][indoor.power.power]
        _seed_match(outdoor, indoor, is_default=True)

    _seed_power_defaults(powers_by_amount)

    multi, _ = _live_get_or_create(
        Item,
        defaults={
            "list_price": Decimal(DAIKIN_MULTI_OUTDOOR_PRICE),
            "internal_code": _outdoor_code("Daikin", 2, 18000),
            "vat_rate": vat23,
            "power": powers_by_amount[18000],
            "sub_family": None,
        },
        brand=daikin,
        kind=Item.Kind.OUTDOOR,
        power=powers_by_amount[18000],
        max_indoor_ports=2,
    )
    for indoor in daikin_indoors:
        if indoor.power.power in (9000, 12000) and indoor.sub_family.name in (
            "Emura",
            "Sensira",
            "Comfora",
            "Perfera",
        ):
            _seed_match(multi, indoor, is_default=False)

    for length, price in TUBING:
        _live_get_or_create(
            TubingLength,
            defaults={"price": Decimal(price)},
            length=Decimal(length),
        )
    for key, value in PARAMETERS:
        _live_get_or_create(Parameter, defaults={"value": value}, key=key)
    _seed_contact_positions()


def _ensure_user(email, password, *, role, is_superuser=False, reset_password=False):
    user = User.objects.filter(email=email).first()
    if user:
        changed = False
        if user.role != role:
            user.role = role
            changed = True
        if is_superuser and not user.is_superuser:
            user.is_superuser = True
            changed = True
        if changed:
            user.save()
        if reset_password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user
    if is_superuser:
        return User.objects.create_superuser(email=email, password=password)
    return User.objects.create_user(email=email, password=password, role=role)


def _is_production_runtime():
    return not settings.DEBUG and not getattr(settings, "TESTING", False)


def seed_agent_users(*, staff_password, admin_password, reset_password=False):
    staff = _ensure_user(
        AGENT_EMAIL,
        staff_password,
        role=User.Role.STAFF,
        reset_password=reset_password,
    )
    admin = _ensure_user(
        AGENT_ADMIN_EMAIL,
        admin_password,
        role=User.Role.ADMIN,
        is_superuser=True,
        reset_password=reset_password,
    )
    return staff, admin


def resolve_agent_passwords(*, staff_password=None, admin_password=None):
    staff = (staff_password or "").strip() or config(AGENT_PASSWORD_ENV, default="")
    admin = (admin_password or "").strip() or config(
        AGENT_ADMIN_PASSWORD_ENV, default=""
    )
    missing = []
    if not staff:
        missing.append(f"--password or {AGENT_PASSWORD_ENV}")
    if not admin:
        missing.append(f"--admin-password or {AGENT_ADMIN_PASSWORD_ENV}")
    if missing:
        raise CommandError("Missing " + " and ".join(missing) + ".")
    return staff, admin


def seed_prod(*, staff_password, admin_password, reset_password=False):
    if _is_production_runtime() and (
        staff_password == DEMO_PASSWORD or admin_password == DEMO_PASSWORD
    ):
        raise CommandError("Refusing the demo password when DEBUG is False.")
    return seed_agent_users(
        staff_password=staff_password,
        admin_password=admin_password,
        reset_password=reset_password,
    )


def _require_catalog_row(qs, *, label):
    try:
        return qs.get()
    except Item.DoesNotExist:
        raise CommandError(
            f"seed_demo: missing catalog row ({label}). Run migrate and seed_catalog first."
        ) from None


def _catalog_indoor(brand, design_line, power_amount):
    return _require_catalog_row(
        Item.objects.filter(
            brand__name=brand,
            sub_family__name=design_line,
            kind=Item.Kind.INDOOR,
            power__power=power_amount,
            power__unit="BTU",
        ),
        label=f"indoor {brand} / {design_line} / {power_amount} BTU",
    )


def _catalog_outdoor(brand, ports, power_amount):
    return _require_catalog_row(
        Item.objects.filter(
            brand__name=brand,
            kind=Item.Kind.OUTDOOR,
            max_indoor_ports=ports,
            power__power=power_amount,
            power__unit="BTU",
        ),
        label=f"outdoor {brand} / {ports}-port / {power_amount} BTU",
    )


def _tubing(length):
    try:
        return TubingLength.objects.get(length=Decimal(length))
    except TubingLength.DoesNotExist:
        raise CommandError(
            f"seed_demo: missing tubing length {length} m. Run migrate first."
        ) from None


def _seed_clients_and_sites(actor):
    sites_by_alias = {}
    for spec in DEMO_CLIENTS:
        client_defaults = {
            "kind": spec.get("kind", Client.Kind.COMPANY),
            "tax_number": spec["tax_number"],
            "street": spec["street"],
            "postal_code": spec["postal_code"],
            "city": spec["city"],
            "country_code": spec.get("country_code", "PT"),
            "phone_country_id": spec.get("phone_country", "PT"),
            "phone": spec.get("phone", ""),
            "email": spec.get("email", ""),
            "contact_name": spec.get("contact_name", ""),
            "contact_position": _resolve_contact_position(
                spec.get("contact_position", "")
            ),
            "created_by": actor,
            "updated_by": actor,
        }
        client, created = _live_get_or_create(
            Client,
            defaults=client_defaults,
            name=spec["name"],
        )
        if created:
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
                created_by=actor,
                updated_by=actor,
            )
        for site_spec in spec["sites"]:
            lookup = {"client": client, "alias_1": site_spec["alias_1"]}
            defaults = {
                "alias_2": site_spec.get("alias_2", ""),
                "alias_3": site_spec.get("alias_3", ""),
                "alias_4": site_spec.get("alias_4", ""),
                "street": site_spec["street"],
                "postal_code": site_spec["postal_code"],
                "city": site_spec["city"],
                "phone_country_id": site_spec.get("phone_country", client.phone_country_id),
                "phone": site_spec.get("phone", client.phone),
                "email": site_spec.get("email", client.email),
                "contact_name": site_spec.get("contact_name", ""),
                "contact_position": _resolve_contact_position(
                    site_spec.get("contact_position", client.contact_position)
                ),
                "notes": site_spec.get("notes", ""),
                "created_by": actor,
                "updated_by": actor,
            }
            site, _ = _live_get_or_create(Site, defaults=defaults, **lookup)
            sites_by_alias[site_spec["alias_1"]] = site
    return sites_by_alias


def _add_lines(proforma, actor, systems):
    for system in systems:
        outdoor = _catalog_outdoor(
            system["brand"], system["ports"], system["outdoor_btu"]
        )
        parent = add_line(proforma, outdoor, actor, quantity=system.get("quantity", 1))
        for indoor_row in system["indoors"]:
            add_line(
                proforma,
                _catalog_indoor(
                    indoor_row.get("brand", system["brand"]),
                    indoor_row["design"],
                    indoor_row["btu"],
                ),
                actor,
                quantity=indoor_row.get("quantity", 1),
                extra_tubing=indoor_row.get("extra_tubing", False),
                tubing_length=_tubing(indoor_row["tubing"])
                if indoor_row.get("tubing")
                else None,
                parent_line=parent,
            )


def _ensure_proforma(site, actor, *, status, lines, accepted=False, rejected=False, **draft_kwargs):
    if site.proformas.exists():
        proforma = site.proformas.order_by("pk").first()
        if (
            accepted
            and proforma.status == Proforma.Status.ISSUED
            and proforma.accepted_at is None
        ):
            accept_proforma(proforma, actor)
        if (
            rejected
            and proforma.status == Proforma.Status.ISSUED
            and proforma.rejected_at is None
        ):
            reject_proforma(proforma, actor)
        return proforma
    proforma = create_draft(site, actor, **draft_kwargs)
    _add_lines(proforma, actor, lines)
    if status == Proforma.Status.ISSUED:
        issue_proforma(proforma, actor)
    if accepted and proforma.status == Proforma.Status.ISSUED:
        accept_proforma(proforma, actor)
    if rejected and proforma.status == Proforma.Status.ISSUED:
        reject_proforma(proforma, actor)
    return proforma


def seed_demo(*, password=DEMO_PASSWORD, reset_password=False):
    if _is_production_runtime():
        raise CommandError(
            "seed_demo is for local development only. Use seed_prod in production."
        )
    seed_catalog()
    admin = _ensure_user(
        DEMO_ADMIN_EMAIL,
        password,
        role=User.Role.ADMIN,
        is_superuser=True,
        reset_password=reset_password,
    )
    manager = _ensure_user(
        DEMO_MANAGER_EMAIL,
        password,
        role=User.Role.STAFF,
        reset_password=reset_password,
    )
    seed_agent_users(
        staff_password=password,
        admin_password=password,
        reset_password=reset_password,
    )
    sites = _seed_clients_and_sites(manager)

    _ensure_proforma(
        sites["Moradia Cascais"],
        manager,
        status=Proforma.Status.ISSUED,
        extra_labour="250.00",
        observations=(
            "House install: one Daikin 2-port outdoor with Emura in the main "
            "bedroom (extra tubing) and a 9k Emura in the suite (extra tubing)."
        ),
        lines=(
            {
                "brand": "Daikin",
                "ports": 2,
                "outdoor_btu": 18000,
                "indoors": (
                    {
                        "design": "Emura",
                        "btu": 12000,
                        "extra_tubing": True,
                        "tubing": "5.00",
                    },
                    {
                        "design": "Emura",
                        "btu": 9000,
                        "extra_tubing": True,
                        "tubing": "3.00",
                    },
                ),
            },
        ),
    )
    _ensure_proforma(
        sites["Bloco Oeiras"],
        manager,
        status=Proforma.Status.DRAFT,
        observations="Draft: extra tubing on entrance B still to confirm.",
        lines=(
            {
                "brand": "Mitsubishi",
                "ports": 1,
                "outdoor_btu": 9000,
                "indoors": ({"design": "Split", "btu": 9000},),
            },
        ),
    )
    _ensure_proforma(
        sites["Apartamento Alfama"],
        manager,
        status=Proforma.Status.ISSUED,
        accepted=True,
        discount_percent="5",
        extra_labour="80.00",
        observations="Alfama refurbishment. Agreed 5% discount.",
        lines=(
            {
                "brand": "LG",
                "ports": 1,
                "outdoor_btu": 18000,
                "indoors": (
                    {
                        "design": "Split",
                        "btu": 18000,
                        "extra_tubing": True,
                        "tubing": "10.00",
                    },
                ),
            },
        ),
    )
    _ensure_proforma(
        sites["Ala Norte"],
        manager,
        status=Proforma.Status.ISSUED,
        rejected=True,
        observations="Client declined this quote.",
        lines=(
            {
                "brand": "Daikin",
                "ports": 1,
                "outdoor_btu": 9000,
                "indoors": ({"design": "Comfora", "btu": 9000},),
            },
        ),
    )
    _ensure_proforma(
        sites["Spa"],
        manager,
        status=Proforma.Status.DRAFT,
        extra_labour="120.00",
        observations="Spa draft: Perfera Floor split. Waiting on measurements.",
        lines=(
            {
                "brand": "Daikin",
                "ports": 1,
                "outdoor_btu": 12000,
                "indoors": ({"design": "Perfera Floor", "btu": 12000},),
            },
        ),
    )
    _ensure_proforma(
        sites["Receção"],
        manager,
        status=Proforma.Status.ISSUED,
        observations="Lobby Sensira split — issued, not accepted (test Change button).",
        lines=(
            {
                "brand": "Daikin",
                "ports": 1,
                "outdoor_btu": 12000,
                "indoors": ({"design": "Sensira", "btu": 12000},),
            },
        ),
    )
    cascais = (
        sites["Moradia Cascais"]
        .proformas.filter(
            status=Proforma.Status.ISSUED,
            superseded_by__isnull=True,
        )
        .order_by("pk")
        .first()
    )
    if cascais is not None:
        try:
            change_proforma(cascais, manager)
        except ValidationError:
            pass
    return {"admin": admin, "manager": manager}
