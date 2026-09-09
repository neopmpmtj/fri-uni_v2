from proformas.agent_cli import (
    AgentCommand,
    add_pagination_arguments,
    list_payload,
    parse_volume,
    serialize_power_row,
)
from proformas.models import Power


class Command(AgentCommand):
    help = "List live power bands (JSON)."

    def add_arguments(self, parser):
        add_pagination_arguments(parser)
        parser.add_argument("--volume", default="")
        parser.add_argument("--has-default", action="store_true")
        parser.add_argument("--search", default="")

    def handle_payload(self, **options):
        qs = Power.objects.select_related("default_indoor")
        raw_volume = (options.get("volume") or "").strip()
        if raw_volume:
            volume = parse_volume(raw_volume)
            qs = qs.filter(
                volume_from_m3__isnull=False,
                volume_to_m3__isnull=False,
                volume_from_m3__lte=volume,
                volume_to_m3__gte=volume,
            )
        if options.get("has_default"):
            qs = qs.filter(default_indoor__isnull=False)
        search = (options.get("search") or "").strip()
        if search:
            qs = qs.filter(unit__icontains=search)
        qs = qs.order_by("power", "unit")
        return list_payload("power", qs, serialize_power_row, options)
