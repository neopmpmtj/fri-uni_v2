from proformas.agent_cli import (
    AgentCommand,
    live_get,
    serialize_client_detail,
    show_payload,
)
from proformas.models import Client


class Command(AgentCommand):
    help = "Show one live client (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle_payload(self, **options):
        client = live_get(Client, options["id"], entity="client")
        return show_payload("client", serialize_client_detail(client))
