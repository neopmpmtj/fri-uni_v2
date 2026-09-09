from django.db.models import Q

from proformas.agent_cli import (
    AgentCommand,
    add_pagination_arguments,
    apply_sort,
    list_payload,
    serialize_client_row,
)
from proformas.models import Client

SORTS = {"name": "name", "tax_number": "tax_number"}


class Command(AgentCommand):
    help = "List live clients (JSON)."

    def add_arguments(self, parser):
        add_pagination_arguments(parser)
        parser.add_argument("--search", default="")
        parser.add_argument("--nif", default="")
        parser.add_argument("--country-code", default="")
        parser.add_argument("--sort", default="name")

    def handle_payload(self, **options):
        qs = Client.objects.all()
        search = (options.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(city__icontains=search)
                | Q(email__icontains=search)
            )
        nif = (options.get("nif") or "").strip()
        if nif:
            qs = qs.filter(tax_number=nif)
        country = (options.get("country_code") or "").strip()
        if country:
            qs = qs.filter(country_code=country.upper())
        qs = apply_sort(qs, options, SORTS, "name")
        return list_payload("client", qs, serialize_client_row, options)
