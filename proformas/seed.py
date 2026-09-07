from decimal import Decimal

from accounts.models import User
from proformas.models import (
    Brand,
    Client,
    ContactPosition,
    Family,
    Item,
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
OUTDOOR_PRICES = {9000: "550.00", 12000: "700.00", 18000: "900.00"}

FAMILY_AC = "Air conditioners"
FAMILY_UNDERFLOOR = "Underfloor heating"
FAMILY_DHW = "Domestic hot water"

AC_SUBFAMILIES = (
    "Split",
    "Sensira",
    "Comfora",
    "Perfera",
    "Perfera Floor",
    "Stylish",
    "Emura",
    "Ururu Sarara",
)

# Named ranges from Daikin PT air-to-air heat pumps (bombas de calor ar-ar):
# https://www.daikin.pt/pt_pt/particular/products-and-advice/product-categories/heat-pumps/air-to-air-heat-pumps.html
DAIKIN_SUBFAMILIES = (
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
DAIKIN_OUTDOOR = {
    "Sensira": {9000: "500.00", 12000: "630.00", 18000: "780.00"},
    "Comfora": {9000: "530.00", 12000: "670.00", 18000: "820.00"},
    "Perfera": {9000: "600.00", 12000: "750.00", 18000: "920.00"},
    "Perfera Floor": {9000: "630.00", 12000: "790.00", 18000: "980.00"},
    "Stylish": {9000: "670.00", 12000: "840.00", 18000: "1020.00"},
    "Emura": {9000: "740.00", 12000: "920.00", 18000: "1120.00"},
    "Ururu Sarara": {9000: "820.00", 12000: "1020.00", 18000: "1280.00"},
}

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
    ("default_upfront_discount_percent", "10"),
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


def _live_get_or_create(model, defaults=None, **lookup):
    obj = model.objects.filter(**lookup).first()
    if obj:
        return obj, False
    data = dict(lookup)
    if defaults:
        data.update(defaults)
    return model.objects.create(**data), True


def _item_code(brand_name, sub_family_name, kind, power_amount):
    brand = BRAND_CODE.get(brand_name, brand_name[:3].upper())
    sub = SUBFAMILY_CODE.get(sub_family_name, sub_family_name[:3].upper())
    kind_ch = "I" if kind == Item.Kind.INDOOR else "O"
    return f"{brand}-{sub}-{kind_ch}-{int(power_amount) // 1000}"


def _seed_powers():
    by_amount = {}
    for amount in BTUS:
        row, _ = _live_get_or_create(
            Power, power=amount, unit="BTU"
        )
        by_amount[amount] = row
    return by_amount


def _seed_capacity_items(
    brand, sub_family, indoor_prices, outdoor_prices, vat_rate, powers_by_amount
):
    for amount in BTUS:
        power = powers_by_amount[amount]
        indoor_defaults = {
            "list_price": Decimal(indoor_prices[amount]),
            "internal_code": _item_code(
                brand.name, sub_family.name, Item.Kind.INDOOR, amount
            ),
            "vat_rate": vat_rate,
            "power": power,
        }
        if amount == 9000:
            indoor_defaults["max_volume_m3"] = Decimal("20")
        _live_get_or_create(
            Item,
            defaults=indoor_defaults,
            brand=brand,
            sub_family=sub_family,
            kind=Item.Kind.INDOOR,
            power=power,
        )
        _live_get_or_create(
            Item,
            defaults={
                "list_price": Decimal(outdoor_prices[amount]),
                "internal_code": _item_code(
                    brand.name, sub_family.name, Item.Kind.OUTDOOR, amount
                ),
                "vat_rate": vat_rate,
                "power": power,
            },
            brand=brand,
            sub_family=sub_family,
            kind=Item.Kind.OUTDOOR,
            power=power,
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
    _live_get_or_create(Family, name=FAMILY_UNDERFLOOR)
    _live_get_or_create(Family, name=FAMILY_DHW)

    daikin, _ = _live_get_or_create(Brand, name="Daikin")
    sub_by_name = {}
    for name in AC_SUBFAMILIES:
        defaults = {"is_default": name == SIMPLE_SUBFAMILY}
        if name in DAIKIN_SUBFAMILIES:
            defaults["brand"] = daikin
        sub, created = _live_get_or_create(
            SubFamily, defaults=defaults, family=ac, name=name
        )
        if (
            not created
            and name in DAIKIN_SUBFAMILIES
            and sub.brand_id != daikin.pk
        ):
            sub.brand = daikin
            sub.save(update_fields=["brand"])
        sub_by_name[name] = sub

    for name in SIMPLE_BRANDS:
        brand, _ = _live_get_or_create(Brand, name=name)
        _seed_capacity_items(
            brand,
            sub_by_name[SIMPLE_SUBFAMILY],
            INDOOR_PRICES,
            OUTDOOR_PRICES,
            vat23,
            powers_by_amount,
        )

    for sub_name in DAIKIN_SUBFAMILIES:
        _seed_capacity_items(
            daikin,
            sub_by_name[sub_name],
            DAIKIN_INDOOR[sub_name],
            DAIKIN_OUTDOOR[sub_name],
            vat23,
            powers_by_amount,
        )

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


def _catalog_item(brand, sub_family, kind, power_amount):
    return Item.objects.get(
        brand__name=brand,
        sub_family__name=sub_family,
        kind=kind,
        power__power=power_amount,
        power__unit="BTU",
    )


def _tubing(length):
    return TubingLength.objects.get(length=Decimal(length))


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


def _add_lines(proforma, actor, lines):
    for row in lines:
        add_line(
            proforma,
            _catalog_item(row["brand"], row["style"], row["kind"], row["btu"]),
            actor,
            quantity=row.get("quantity", 1),
            extra_tubing=row.get("extra_tubing", False),
            tubing_length=_tubing(row["tubing"]) if row.get("tubing") else None,
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
    sites = _seed_clients_and_sites(manager)

    indoor = Item.Kind.INDOOR
    outdoor = Item.Kind.OUTDOOR

    _ensure_proforma(
        sites["Moradia Cascais"],
        manager,
        status=Proforma.Status.ISSUED,
        extra_labour="250.00",
        observations=(
            "House install: Emura in the main bedroom with extra tubing, "
            "and a 9k unit in the suite also with extra tubing."
        ),
        lines=(
            {
                "brand": "Daikin",
                "style": "Emura",
                "kind": indoor,
                "btu": 12000,
                "extra_tubing": True,
                "tubing": "5.00",
            },
            {"brand": "Daikin", "style": "Emura", "kind": outdoor, "btu": 12000},
            {
                "brand": "Daikin",
                "style": "Emura",
                "kind": indoor,
                "btu": 9000,
                "extra_tubing": True,
                "tubing": "3.00",
            },
            {"brand": "Daikin", "style": "Emura", "kind": outdoor, "btu": 9000},
        ),
    )
    _ensure_proforma(
        sites["Bloco Oeiras"],
        manager,
        status=Proforma.Status.DRAFT,
        observations="Draft: extra tubing on entrance B still to confirm.",
        lines=(
            {"brand": "Mitsubishi", "style": "Split", "kind": indoor, "btu": 9000},
            {"brand": "Mitsubishi", "style": "Split", "kind": outdoor, "btu": 9000},
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
                "style": "Split",
                "kind": indoor,
                "btu": 18000,
                "extra_tubing": True,
                "tubing": "10.00",
            },
            {"brand": "LG", "style": "Split", "kind": outdoor, "btu": 18000},
        ),
    )
    _ensure_proforma(
        sites["Ala Norte"],
        manager,
        status=Proforma.Status.ISSUED,
        rejected=True,
        observations="Client declined this quote.",
        lines=(
            {"brand": "Daikin", "style": "Comfora", "kind": indoor, "btu": 9000},
            {"brand": "Daikin", "style": "Comfora", "kind": outdoor, "btu": 9000},
        ),
    )
    _ensure_proforma(
        sites["Spa"],
        manager,
        status=Proforma.Status.DRAFT,
        extra_labour="120.00",
        observations="Spa draft: Perfera Floor. Waiting on measurements.",
        lines=(
            {"brand": "Daikin", "style": "Perfera Floor", "kind": indoor, "btu": 12000},
            {"brand": "Daikin", "style": "Perfera Floor", "kind": outdoor, "btu": 12000},
        ),
    )
    _ensure_proforma(
        sites["Receção"],
        manager,
        status=Proforma.Status.ISSUED,
        observations="Lobby Sensira pair — issued, not accepted (test Change button).",
        lines=(
            {"brand": "Daikin", "style": "Sensira", "kind": indoor, "btu": 12000},
            {"brand": "Daikin", "style": "Sensira", "kind": outdoor, "btu": 12000},
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
