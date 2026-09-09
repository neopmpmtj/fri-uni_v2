from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_get,
    resolve_user,
    show_payload,
)
from proformas.models import Site
from proformas.services import delete_site


class Command(AgentCommand):
    help = "Soft-delete a site (admin only, JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int, required=True)

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        site = live_get(Site, options["id"], entity="site")
        delete_site(site, user)
        return show_payload("site", {"id": options["id"], "deleted": True})
