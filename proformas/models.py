from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.models.functions import Lower
from django.utils import timezone


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = LiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["deleted_at", "deleted_by", "updated_at"])


class ActorType(models.TextChoices):
    USER = "user", "User"
    SYSTEM = "system", "System"


class Parameter(AuditedModel):
    key = models.CharField(max_length=64)
    value = models.TextField()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["key"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_parameter_key",
            )
        ]

    def __str__(self):
        return self.key


class Country(models.Model):
    code = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=64)
    dial_code = models.CharField(max_length=4)
    phone_national_digits = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class ContactPosition(AuditedModel):
    """Contact role / job title for client and site contacts."""

    name = models.CharField(max_length=64)

    class Meta:
        ordering = ["name"]
        constraints = [
            UniqueConstraint(
                Lower("name"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_contact_position_name_ci",
            ),
        ]

    def __str__(self):
        return self.name


class Client(AuditedModel):
    class Kind(models.TextChoices):
        PERSON = "person", "Person"
        COMPANY = "company", "Company"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    name = models.CharField(max_length=255)
    tax_number = models.CharField(max_length=9, blank=True)
    street = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=8, blank=True)
    city = models.CharField(max_length=128, blank=True)
    country_code = models.CharField(max_length=2, default="PT")
    phone_country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        default="PT",
        related_name="+",
    )
    phone = models.CharField(max_length=9)
    email = models.EmailField()
    contact_name = models.CharField(max_length=255, blank=True)
    contact_position = models.ForeignKey(
        ContactPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_client_name",
            ),
            UniqueConstraint(
                fields=["tax_number"],
                condition=Q(deleted_at__isnull=True) & ~Q(tax_number=""),
                name="uniq_live_client_tax_number",
            ),
        ]

    def __str__(self):
        return self.name


class Site(AuditedModel):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="sites")
    is_headquarters = models.BooleanField(default=False)
    alias_1 = models.CharField(max_length=255)
    alias_2 = models.CharField(max_length=255, blank=True)
    alias_3 = models.CharField(max_length=255, blank=True)
    alias_4 = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=8)
    city = models.CharField(max_length=128)
    phone_country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        default="PT",
        related_name="+",
    )
    phone = models.CharField(max_length=9)
    email = models.EmailField()
    contact_name = models.CharField(max_length=255, blank=True)
    contact_position = models.ForeignKey(
        ContactPosition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["client"],
                condition=Q(deleted_at__isnull=True, is_headquarters=True),
                name="uniq_live_site_hq_per_client",
            )
        ]

    def __str__(self):
        return self.alias_1


class Brand(AuditedModel):
    """Manufacturer (data-points table `brands`)."""

    name = models.CharField(max_length=128)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_brand_name",
            ),
            UniqueConstraint(
                fields=["is_default"],
                condition=Q(deleted_at__isnull=True, is_default=True),
                name="uniq_live_default_brand",
            ),
        ]

    def __str__(self):
        return self.name


class Family(AuditedModel):
    """Product category (AC, underfloor, DHW)."""

    name = models.CharField(max_length=128)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "families"
        constraints = [
            UniqueConstraint(
                Lower("name"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_family_name_ci",
            ),
            UniqueConstraint(
                fields=["is_default"],
                condition=Q(deleted_at__isnull=True, is_default=True),
                name="uniq_live_default_family",
            ),
        ]

    def __str__(self):
        return self.name


class SubFamily(AuditedModel):
    """Named range under a family (was Style). Optional manufacturer."""

    family = models.ForeignKey(
        Family, on_delete=models.PROTECT, related_name="sub_families"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="owned_sub_families",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=128)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "sub-family"
        verbose_name_plural = "sub-families"
        constraints = [
            UniqueConstraint(
                Lower("name"),
                "family",
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_subfamily_name_ci_per_family",
            ),
            UniqueConstraint(
                fields=["family"],
                condition=Q(deleted_at__isnull=True, is_default=True),
                name="uniq_live_default_subfamily_per_family",
            ),
        ]

    def __str__(self):
        return f"{self.family.name} / {self.name}"


class Power(AuditedModel):
    """Catalog power rating (data-points table `powers`)."""

    power = models.IntegerField()
    unit = models.CharField(max_length=32)

    class Meta:
        ordering = ["power", "unit"]
        constraints = [
            UniqueConstraint(
                "power",
                Lower("unit"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_power_unit_ci",
            ),
        ]

    def __str__(self):
        return f"{self.power} {self.unit}"


class VatRate(AuditedModel):
    """Catalog IVA lookup (data-points table `vat_rates`)."""

    code = models.CharField(max_length=32)
    label = models.CharField(max_length=64)
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["rate"]
        constraints = [
            UniqueConstraint(
                Lower("code"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_vat_rate_code_ci",
            ),
            UniqueConstraint(
                fields=["is_default"],
                condition=Q(deleted_at__isnull=True, is_default=True),
                name="uniq_live_default_vat_rate",
            ),
            models.CheckConstraint(
                condition=Q(rate__gte=0, rate__lte=1),
                name="vat_rate_gte_zero_lte_one",
            ),
        ]

    def __str__(self):
        return self.label

    def as_percent(self):
        return (self.rate * 100).quantize(Decimal("0.01"))


class Item(AuditedModel):
    """Catalog machine (data-points table `items`)."""

    class Kind(models.TextChoices):
        INDOOR = "indoor", "Indoor"
        OUTDOOR = "outdoor", "Outdoor"

    sub_family = models.ForeignKey(
        SubFamily, on_delete=models.PROTECT, related_name="items"
    )
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="items")
    vat_rate = models.ForeignKey(
        VatRate, on_delete=models.PROTECT, related_name="items"
    )
    internal_code = models.CharField(max_length=64)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    power = models.ForeignKey(
        Power, on_delete=models.PROTECT, related_name="items"
    )
    max_volume_m3 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    list_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                Lower("internal_code"),
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_item_internal_code_ci",
            ),
            UniqueConstraint(
                fields=["sub_family", "brand"],
                condition=Q(deleted_at__isnull=True, is_default=True),
                name="uniq_live_default_item_per_subfamily_brand",
            ),
            UniqueConstraint(
                fields=["sub_family", "brand", "kind", "power"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_item_identity",
            ),
        ]

    def __str__(self):
        return (
            f"{self.internal_code} — {self.sub_family.name} "
            f"{self.kind} {self.power}"
        )


class TubingLength(AuditedModel):
    length = models.DecimalField(max_digits=8, decimal_places=2)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["length"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_tubing_length",
            )
        ]

    def __str__(self):
        return f"{self.length} m"


class Proforma(AuditedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"

    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="proformas")
    number = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    replaces = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    upfront_discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    extra_labour = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observations = models.TextField(blank=True)
    equipment_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    tubing_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_tubing_metres = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    grand_total = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    client_name = models.CharField(max_length=255, blank=True)
    client_kind = models.CharField(max_length=16, blank=True)
    client_tax_number = models.CharField(max_length=9, blank=True)
    client_street = models.CharField(max_length=255, blank=True)
    client_postal_code = models.CharField(max_length=8, blank=True)
    client_city = models.CharField(max_length=128, blank=True)
    client_country_code = models.CharField(max_length=2, blank=True)
    client_phone = models.CharField(max_length=64, blank=True)
    client_email = models.CharField(max_length=254, blank=True)
    site_alias_1 = models.CharField(max_length=255, blank=True)
    site_alias_2 = models.CharField(max_length=255, blank=True)
    site_alias_3 = models.CharField(max_length=255, blank=True)
    site_alias_4 = models.CharField(max_length=255, blank=True)
    site_street = models.CharField(max_length=255, blank=True)
    site_postal_code = models.CharField(max_length=32, blank=True)
    site_city = models.CharField(max_length=128, blank=True)
    site_notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["number"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_live_proforma_number",
            )
        ]

    def __str__(self):
        return self.number

    @property
    def can_edit(self):
        return self.status == self.Status.DRAFT

    @property
    def can_change(self):
        return (
            self.status == self.Status.ISSUED
            and self.accepted_at is None
            and self.rejected_at is None
            and self.superseded_by_id is None
        )

    @property
    def is_superseded(self):
        return self.superseded_by_id is not None


class ProformaLine(AuditedModel):
    proforma = models.ForeignKey(Proforma, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name="proforma_lines"
    )
    quantity = models.IntegerField(default=1)
    extra_tubing = models.BooleanField(default=False)
    tubing_length = models.ForeignKey(
        TubingLength,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="proforma_lines",
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tubing_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    brand_name = models.CharField(max_length=128, blank=True)
    family_name = models.CharField(max_length=128, blank=True)
    sub_family_name = models.CharField(max_length=128, blank=True)
    internal_code = models.CharField(max_length=64, blank=True)
    kind = models.CharField(max_length=16, blank=True)
    power_value = models.IntegerField(null=True, blank=True)
    power_unit = models.CharField(max_length=32, blank=True)
    tubing_length_value = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.proforma.number} line"


class ChangeLog(AuditedModel):
    entity_type = models.CharField(max_length=64)
    entity_id = models.PositiveBigIntegerField()
    field = models.CharField(max_length=64)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="change_logs",
    )
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.USER
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.entity_type}.{self.field}"


class ActivityLog(AuditedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_logs",
    )
    actor_type = models.CharField(
        max_length=16, choices=ActorType.choices, default=ActorType.USER
    )
    action = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64)
    object_id = models.PositiveBigIntegerField()
    occurred_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return self.action
