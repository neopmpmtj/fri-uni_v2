from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import (
    Brand,
    Client,
    ContactPosition,
    Country,
    Family,
    Item,
    ItemMatch,
    Parameter,
    Power,
    ProformaLine,
    Site,
    SubFamily,
    TubingLength,
    VatRate,
)
from .services import (
    configure_nine_digit_form_field,
    discount_percent_value,
    normalize_postal_code,
    percent_to_rate,
    validate_internal_code,
    validate_item_identity,
    validate_item_kind_fields,
    validate_phone_number,
    validate_power_default_indoor,
    validate_power_uniqueness,
    validate_power_volume_band,
    validate_tax_number,
    validate_vat_code,
)


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            "kind",
            "name",
            "tax_number",
            "street",
            "postal_code",
            "city",
            "country_code",
            "phone_country",
            "phone",
            "email",
            "contact_name",
            "contact_position",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["kind"].initial = Client.Kind.PERSON
            self.fields["country_code"].initial = "PT"
        self.fields["country_code"].widget = forms.Select(
            choices=[("PT", "Portugal")]
        )
        configure_nine_digit_form_field(self.fields["tax_number"], required=False)
        self.fields["street"].required = False
        self.fields["postal_code"].required = False
        self.fields["city"].required = False
        self.fields["phone_country"].queryset = Country.objects.order_by("name")
        self.fields["phone_country"].disabled = True
        self.fields["phone_country"].label_from_instance = (
            lambda obj: f"{obj.name} (+{obj.dial_code})"
        )
        if not self.instance.pk:
            self.fields["phone_country"].initial = "PT"
        configure_nine_digit_form_field(self.fields["phone"], required=True)
        self.fields["email"].required = True
        self.fields["contact_name"].required = False
        self.fields["contact_position"].queryset = ContactPosition.objects.order_by("name")
        self.fields["contact_position"].required = False

    def clean(self):
        cleaned = super().clean()
        if self.fields["phone_country"].disabled:
            if self.instance.pk and self.instance.phone_country_id:
                cleaned["phone_country"] = self.instance.phone_country
            else:
                cleaned["phone_country"] = Country.objects.get(code="PT")
        return cleaned

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Client.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live client with this name already exists.")
        return name

    def clean_tax_number(self):
        raw = (self.cleaned_data.get("tax_number") or "").strip()
        if not raw:
            return ""
        tax_number = validate_tax_number(raw)
        qs = Client.objects.filter(tax_number=tax_number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live client with this NIF already exists.")
        return tax_number

    def clean_phone(self):
        if self.instance.pk and self.instance.phone_country_id:
            country_code = self.instance.phone_country_id
        else:
            country_code = "PT"
        return validate_phone_number(
            self.cleaned_data["phone"], country_code=country_code
        )

    def clean_postal_code(self):
        raw = (self.cleaned_data.get("postal_code") or "").strip()
        if not raw:
            return ""
        return normalize_postal_code(raw)

    def clean_street(self):
        return self.cleaned_data["street"].strip()

    def clean_city(self):
        return self.cleaned_data["city"].strip()

    def clean_contact_name(self):
        return (self.cleaned_data.get("contact_name") or "").strip()


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = (
            "client",
            "alias_1",
            "alias_2",
            "alias_3",
            "alias_4",
            "street",
            "postal_code",
            "city",
            "phone_country",
            "phone",
            "email",
            "contact_name",
            "contact_position",
            "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.is_headquarters:
            self.fields["client"].disabled = True
        self.fields["phone_country"].queryset = Country.objects.order_by("name")
        self.fields["phone_country"].disabled = True
        self.fields["phone_country"].label_from_instance = (
            lambda obj: f"{obj.name} (+{obj.dial_code})"
        )
        if not self.instance.pk:
            self.fields["phone_country"].initial = "PT"
        configure_nine_digit_form_field(self.fields["phone"], required=True)
        self.fields["email"].required = True
        self.fields["contact_name"].required = False
        self.fields["contact_position"].queryset = ContactPosition.objects.order_by("name")
        self.fields["contact_position"].required = False

    def clean(self):
        cleaned = super().clean()
        if self.fields["phone_country"].disabled:
            if self.instance.pk and self.instance.phone_country_id:
                cleaned["phone_country"] = self.instance.phone_country
            else:
                cleaned["phone_country"] = Country.objects.get(code="PT")
        return cleaned

    def clean_client(self):
        client = self.cleaned_data["client"]
        if self.instance.pk and self.instance.is_headquarters:
            if client != self.instance.client:
                raise ValidationError(
                    "Cannot reassign the headquarters site to another client."
                )
        return client

    def clean_postal_code(self):
        return normalize_postal_code(self.cleaned_data["postal_code"])

    def clean_phone(self):
        if self.instance.pk and self.instance.phone_country_id:
            country_code = self.instance.phone_country_id
        else:
            country_code = "PT"
        return validate_phone_number(
            self.cleaned_data["phone"], country_code=country_code
        )

    def clean_street(self):
        return self.cleaned_data["street"].strip()

    def clean_city(self):
        return self.cleaned_data["city"].strip()

    def clean_alias_1(self):
        return self.cleaned_data["alias_1"].strip()

    def clean_contact_name(self):
        return (self.cleaned_data.get("contact_name") or "").strip()


class SiteClientSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is not None and hasattr(instance, "client_id"):
            option["attrs"]["data-client"] = str(instance.client_id)
        return option


class NewDraftForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.none())
    site = forms.ModelChoiceField(queryset=Site.objects.none(), widget=SiteClientSelect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.order_by("name")
        self.fields["site"].queryset = Site.objects.select_related("client").order_by(
            "-is_headquarters", "alias_1"
        )
        if self.is_bound:
            client_id = self.data.get("client")
            if client_id:
                self.fields["site"].queryset = self.fields["site"].queryset.filter(
                    client_id=client_id
                )

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get("client")
        site = cleaned_data.get("site")
        if client and site and site.client_id != client.pk:
            raise ValidationError("Site does not belong to the selected client.")
        return cleaned_data


class ProformaHeaderForm(forms.Form):
    upfront_discount_percent = forms.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100
    )
    extra_labour = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    observations = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    override_checks = forms.BooleanField(required=False)


class DefaultSplitForm(forms.Form):
    volume_m3 = forms.DecimalField(
        min_value=0, max_digits=8, decimal_places=2, label="Room volume m3"
    )


class DataDefaultSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        instance = getattr(value, "instance", None)
        if instance is None:
            return option
        if getattr(instance, "is_default", False):
            option["attrs"]["data-default"] = "1"
        if isinstance(instance, SubFamily):
            option["attrs"]["data-family"] = str(instance.family_id)
            if instance.brand_id:
                option["attrs"]["data-brand"] = str(instance.brand_id)
        if isinstance(instance, Item):
            option["attrs"]["data-sub-family"] = (
                str(instance.sub_family_id) if instance.sub_family_id else ""
            )
            option["attrs"]["data-brand"] = str(instance.brand_id)
        return option


class ProformaLineForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1)
    family = forms.ModelChoiceField(
        queryset=Family.objects.none(), required=False, widget=DataDefaultSelect
    )
    sub_family = forms.ModelChoiceField(
        queryset=SubFamily.objects.none(), required=False, widget=DataDefaultSelect
    )
    manufacturer = forms.ModelChoiceField(
        queryset=Brand.objects.none(), required=False, widget=DataDefaultSelect
    )
    parent_line = forms.ModelChoiceField(
        queryset=ProformaLine.objects.none(), required=False, widget=forms.HiddenInput
    )

    class Meta:
        model = ProformaLine
        fields = ("item", "quantity", "extra_tubing", "tubing_length")
        widgets = {"item": DataDefaultSelect}

    def __init__(
        self,
        *args,
        parent_line=None,
        outdoor_only=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.parent_line_obj = parent_line
        self.outdoor_only = outdoor_only
        items = Item.objects.select_related(
            "sub_family__family", "brand", "power"
        ).order_by("internal_code")
        if outdoor_only:
            items = items.filter(kind=Item.Kind.OUTDOOR)
            instance_item = (
                self.instance.item
                if self.instance.pk and self.instance.item_id
                else None
            )
            if instance_item is None:
                items = items.filter(max_indoor_ports__gte=2)
            else:
                ports = instance_item.max_indoor_ports or 0
                if ports <= 1:
                    port_q = Q(max_indoor_ports=1)
                else:
                    port_q = Q(max_indoor_ports__gte=2)
                items = items.filter(port_q | Q(pk=instance_item.pk))
        elif parent_line is not None:
            indoor_ids = ItemMatch.objects.filter(
                outdoor=parent_line.item
            ).values_list("indoor_id", flat=True)
            items = items.filter(kind=Item.Kind.INDOOR, pk__in=indoor_ids)
        else:
            items = items.filter(kind=Item.Kind.INDOOR)
        self.fields["item"].queryset = items
        self.fields["item"].label_from_instance = (
            lambda obj: f"{obj.internal_code} — {obj.kind} {obj.power}"
        )
        self.fields["family"].queryset = Family.objects.order_by("name")
        self.fields["sub_family"].queryset = SubFamily.objects.select_related(
            "family", "brand"
        ).order_by("name")
        self.fields["manufacturer"].queryset = Brand.objects.order_by("name")
        self.fields["tubing_length"].queryset = TubingLength.objects.order_by("length")
        self.fields["tubing_length"].required = False
        self.fields["parent_line"].queryset = ProformaLine.objects.all()
        if parent_line is not None:
            self.fields["parent_line"].initial = parent_line.pk
        if outdoor_only:
            self.fields["extra_tubing"].initial = False
        lengths = self.fields["tubing_length"].queryset
        if lengths.exists():
            self.fields["tubing_length"].empty_label = None
            if not (self.instance.pk and self.instance.tubing_length_id):
                self.fields["tubing_length"].initial = lengths.first()
        if self.instance.pk and self.instance.item_id:
            item = self.instance.item
            if item.sub_family_id:
                self.fields["family"].initial = item.sub_family.family_id
                self.fields["sub_family"].initial = item.sub_family_id
            self.fields["manufacturer"].initial = item.brand_id
            if self.instance.parent_line_id:
                self.fields["parent_line"].initial = self.instance.parent_line_id

    def clean(self):
        cleaned = super().clean()
        item = cleaned.get("item")
        extra = cleaned.get("extra_tubing")
        if extra and not cleaned.get("tubing_length"):
            raise ValidationError("Tubing length is required when extra tubing is needed.")
        if item and item.kind == Item.Kind.OUTDOOR:
            cleaned["extra_tubing"] = False
            cleaned["tubing_length"] = None
        parent = cleaned.get("parent_line") or self.parent_line_obj
        if parent:
            cleaned["parent_line"] = parent
        return cleaned


class ContactPositionForm(forms.ModelForm):
    class Meta:
        model = ContactPosition
        fields = ("name",)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = ContactPosition.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live position with this name already exists.")
        return name


class FamilyForm(forms.ModelForm):
    class Meta:
        model = Family
        fields = ("name", "is_default")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Family.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live family with this name already exists.")
        return name


class SubFamilyForm(forms.ModelForm):
    class Meta:
        model = SubFamily
        fields = ("family", "name", "brand", "is_default")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = Brand.objects.order_by("name")
        self.fields["brand"].required = False

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("name") or "").strip()
        family = cleaned.get("family")
        cleaned["name"] = name
        if name and family:
            qs = SubFamily.objects.filter(family=family, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    "A live sub-family with this name already exists in that family."
                )
        return cleaned


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ("name", "is_default")

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        qs = Brand.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live manufacturer with this name already exists.")
        return name


class ItemForm(forms.ModelForm):
    family = forms.ModelChoiceField(
        queryset=Family.objects.none(), required=False, widget=DataDefaultSelect
    )
    default_outdoor = forms.ModelChoiceField(
        queryset=Item.objects.none(), required=False
    )
    compatible_indoors = forms.ModelMultipleChoiceField(
        queryset=Item.objects.none(), required=False
    )

    class Meta:
        model = Item
        fields = (
            "sub_family",
            "brand",
            "vat_rate",
            "internal_code",
            "kind",
            "power",
            "max_indoor_ports",
            "is_default",
        )
        widgets = {"sub_family": DataDefaultSelect, "vat_rate": DataDefaultSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["family"].queryset = Family.objects.order_by("name")
        self.fields["sub_family"].queryset = SubFamily.objects.select_related(
            "family", "brand"
        ).order_by("family__name", "name")
        self.fields["sub_family"].required = False
        self.fields["brand"].queryset = Brand.objects.order_by("name")
        self.fields["brand"].required = False
        self.fields["power"].queryset = Power.objects.order_by("power", "unit")
        self.fields["power"].label_from_instance = lambda obj: str(obj)
        self.fields["vat_rate"].queryset = VatRate.objects.order_by("rate")
        self.fields["max_indoor_ports"].required = False
        self.fields["default_outdoor"].queryset = Item.objects.filter(
            kind=Item.Kind.OUTDOOR, max_indoor_ports=1
        ).order_by("internal_code")
        self.fields["compatible_indoors"].queryset = Item.objects.filter(
            kind=Item.Kind.INDOOR
        ).order_by("internal_code")
        if self.instance.pk and self.instance.sub_family_id:
            self.fields["family"].initial = self.instance.sub_family.family_id
        elif not self.instance.pk:
            default_vat = VatRate.objects.filter(is_default=True).first()
            if default_vat:
                self.fields["vat_rate"].initial = default_vat.pk
        if self.instance.pk:
            if self.instance.kind == Item.Kind.INDOOR:
                match = ItemMatch.objects.filter(
                    indoor=self.instance, is_default=True
                ).first()
                if match:
                    self.fields["default_outdoor"].initial = match.outdoor_id
            else:
                self.fields["compatible_indoors"].initial = ItemMatch.objects.filter(
                    outdoor=self.instance
                ).values_list("indoor_id", flat=True)

    def clean_internal_code(self):
        return validate_internal_code(
            self.cleaned_data.get("internal_code"),
            exclude_item_id=self.instance.pk,
        )

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        sub_family = cleaned.get("sub_family")
        if kind == Item.Kind.OUTDOOR:
            cleaned["sub_family"] = None
            if not cleaned.get("brand"):
                self.add_error("brand", "This field is required.")
                return cleaned
        else:
            cleaned["max_indoor_ports"] = None
            if sub_family and sub_family.brand_id:
                cleaned["brand"] = sub_family.brand
            elif not cleaned.get("brand"):
                self.add_error("brand", "This field is required.")
                return cleaned
        try:
            validate_item_kind_fields(
                kind=kind,
                sub_family=cleaned.get("sub_family"),
                max_indoor_ports=cleaned.get("max_indoor_ports"),
            )
            validate_item_identity(
                sub_family=cleaned.get("sub_family"),
                brand=cleaned.get("brand"),
                kind=kind,
                power=cleaned.get("power"),
                max_indoor_ports=cleaned.get("max_indoor_ports"),
                exclude_item_id=self.instance.pk,
            )
        except ValidationError as exc:
            self.add_error(None, exc)
        return cleaned


class ItemPriceForm(forms.Form):
    list_price = forms.DecimalField(max_digits=12, decimal_places=2)
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class VatRateForm(forms.ModelForm):
    percent = forms.DecimalField(max_digits=6, decimal_places=2, min_value=0, max_value=100)

    class Meta:
        model = VatRate
        fields = ("code", "label", "is_default")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.rate is not None:
            self.fields["percent"].initial = self.instance.as_percent()

    def clean_code(self):
        return validate_vat_code(self.cleaned_data.get("code"), exclude_id=self.instance.pk)

    def clean(self):
        cleaned = super().clean()
        percent = cleaned.get("percent")
        if percent is not None:
            cleaned["rate"] = percent_to_rate(percent)
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.rate = self.cleaned_data["rate"]
        if commit:
            obj.save()
        return obj


class PowerForm(forms.ModelForm):
    class Meta:
        model = Power
        fields = (
            "power",
            "unit",
            "volume_from_m3",
            "volume_to_m3",
            "default_indoor",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["volume_from_m3"].required = False
        self.fields["volume_to_m3"].required = False
        self.fields["default_indoor"].required = False
        indoors = Item.objects.filter(kind=Item.Kind.INDOOR).select_related("power")
        if self.instance.pk:
            indoors = indoors.filter(power=self.instance)
        else:
            indoors = indoors.none()
        self.fields["default_indoor"].queryset = indoors.order_by("internal_code")
        self.fields["default_indoor"].label_from_instance = (
            lambda obj: f"{obj.internal_code} — {obj.power}"
        )

    def clean(self):
        cleaned = super().clean()
        power = cleaned.get("power")
        unit = cleaned.get("unit")
        if power is not None and unit is not None:
            cleaned["unit"] = validate_power_uniqueness(
                power, unit, exclude_id=self.instance.pk
            )
        self.instance.power = power
        self.instance.unit = cleaned.get("unit") or self.instance.unit
        self.instance.volume_from_m3 = cleaned.get("volume_from_m3")
        self.instance.volume_to_m3 = cleaned.get("volume_to_m3")
        self.instance.default_indoor = cleaned.get("default_indoor")
        try:
            validate_power_volume_band(self.instance, exclude_id=self.instance.pk)
            validate_power_default_indoor(self.instance)
        except ValidationError as exc:
            self.add_error(None, exc)
        return cleaned


class ParameterForm(forms.ModelForm):
    class Meta:
        model = Parameter
        fields = ("value",)
        widgets = {"value": forms.TextInput()}

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get("value")
        if (
            value is not None
            and self.instance.pk
            and self.instance.key == "default_upfront_discount_percent"
        ):
            try:
                discount_percent_value(value)
            except ValidationError as exc:
                self.add_error("value", exc)
        return cleaned


class TubingLengthForm(forms.ModelForm):
    reason = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    class Meta:
        model = TubingLength
        fields = ("length", "price")

    def clean_length(self):
        length = self.cleaned_data["length"]
        qs = TubingLength.objects.filter(length=length)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A live tubing length with this value already exists.")
        return length

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk:
            return cleaned
        new_price = cleaned.get("price")
        if new_price is not None and new_price != self.instance.price:
            if not (cleaned.get("reason") or "").strip():
                self.add_error("reason", "A reason is required when changing tubing price.")
        return cleaned

