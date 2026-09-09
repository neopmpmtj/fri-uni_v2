from django.db.models import Q

from proformas.agent_cli import (
    AgentCommand,
    add_pagination_arguments,
    apply_sort,
    list_payload,
    serialize_site_row,
)
from proformas.models import Site

SORTS = {"alias_1": "alias_1"}


class Command(AgentCommand):
    help = "List live sites (JSON)."

    def add_arguments(self, parser):
        add_pagination_arguments(parser)
        parser.add_argument("--client", type=int)
        parser.add_argument("--search", default="")
        parser.add_argument("--sort", default="alias_1")

    def handle_payload(self, **options):
        qs = Site.objects.select_related("client")
        if options.get("client") is not None:
            qs = qs.filter(client_id=options["client"])
        search = (options.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(alias_1__icontains=search)
                | Q(alias_2__icontains=search)
                | Q(alias_3__icontains=search)
                | Q(alias_4__icontains=search)
                | Q(city__icontains=search)
            )
        qs = apply_sort(qs, options, SORTS, "alias_1")
        return list_payload("site", qs, serialize_site_row, options)
