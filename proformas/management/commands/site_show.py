from proformas.agent_cli import (
    AgentCommand,
    live_get,
    serialize_site_detail,
    show_payload,
)
from proformas.models import Site


class Command(AgentCommand):
    help = "Show one live site (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle_payload(self, **options):
        site = live_get(Site, options["id"], entity="site")
        return show_payload(
            "site", serialize_site_detail(Site.objects.select_related("client").get(pk=site.pk))
        )
