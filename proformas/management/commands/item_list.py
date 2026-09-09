from proformas.agent_cli import (
    AgentCommand,
    add_pagination_arguments,
    list_payload,
    serialize_item_row,
)
from proformas.models import Item


class Command(AgentCommand):
    help = "List live catalog items (JSON)."

    def add_arguments(self, parser):
        add_pagination_arguments(parser)
        parser.add_argument("--kind", choices=["indoor", "outdoor"])
        parser.add_argument("--family", type=int)
        parser.add_argument("--design-line", type=int)
        parser.add_argument("--brand", type=int)
        parser.add_argument("--power", type=int)
        parser.add_argument("--search", default="")
        parser.add_argument("--code", default="")
        parser.add_argument("--default", action="store_true")

    def handle_payload(self, **options):
        qs = Item.objects.select_related(
            "power", "brand", "sub_family__family", "vat_rate"
        )
        kind = options.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        if options.get("family") is not None:
            qs = qs.filter(sub_family__family_id=options["family"])
        if options.get("design_line") is not None:
            qs = qs.filter(sub_family_id=options["design_line"])
        if options.get("brand") is not None:
            qs = qs.filter(brand_id=options["brand"])
        if options.get("power") is not None:
            qs = qs.filter(power_id=options["power"])
        search = (options.get("search") or "").strip()
        if search:
            qs = qs.filter(internal_code__icontains=search)
        code = (options.get("code") or "").strip()
        if code:
            qs = qs.filter(internal_code__iexact=code)
        if options.get("default"):
            qs = qs.filter(is_default=True)
        qs = qs.order_by("internal_code")
        return list_payload("item", qs, serialize_item_row, options)
