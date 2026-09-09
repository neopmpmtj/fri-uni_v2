from django.core.management.base import CommandError
from django.utils.dateparse import parse_date

from proformas.agent_cli import (
    AgentCommand,
    add_pagination_arguments,
    apply_sort,
    list_payload,
    serialize_proforma_row,
)
from proformas.models import Proforma

SORTS = {
    "number": "-number",
    "status": "status",
    "created_at": "-created_at",
}


def _parse_day(raw, flag):
    raw = (raw or "").strip()
    if not raw:
        return None
    value = parse_date(raw)
    if value is None:
        raise CommandError(f"{flag} must be YYYY-MM-DD.")
    return value


class Command(AgentCommand):
    help = "List live proformas (JSON)."

    def add_arguments(self, parser):
        add_pagination_arguments(parser)
        parser.add_argument("--status", choices=["draft", "issued"])
        parser.add_argument("--client", type=int)
        parser.add_argument("--site", type=int)
        parser.add_argument("--number", default="")
        parser.add_argument("--from", dest="date_from", default="")
        parser.add_argument("--to", dest="date_to", default="")
        parser.add_argument("--sort", default="number")

    def handle_payload(self, **options):
        qs = Proforma.objects.select_related("site__client")
        if options.get("status"):
            qs = qs.filter(status=options["status"])
        if options.get("client") is not None:
            qs = qs.filter(site__client_id=options["client"])
        if options.get("site") is not None:
            qs = qs.filter(site_id=options["site"])
        number = (options.get("number") or "").strip()
        if number:
            qs = qs.filter(number=number)
        date_from = _parse_day(options.get("date_from"), "--from")
        date_to = _parse_day(options.get("date_to"), "--to")
        if date_from:
            qs = qs.filter(
                created_at__date__gte=date_from,
            )
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = apply_sort(qs, options, SORTS, "number")
        return list_payload("proforma", qs, serialize_proforma_row, options)
