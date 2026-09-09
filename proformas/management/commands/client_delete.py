from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_get,
    resolve_user,
    show_payload,
)
from proformas.models import Client
from proformas.services import delete_client


class Command(AgentCommand):
    help = "Soft-delete a client (admin only, JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int, required=True)

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        client = live_get(Client, options["id"], entity="client")
        delete_client(client, user)
        return show_payload("client", {"id": options["id"], "deleted": True})
