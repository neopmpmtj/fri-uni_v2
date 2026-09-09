from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_line,
    proforma_detail_payload,
    resolve_user,
)
from proformas.services import remove_line


class Command(AgentCommand):
    help = "Remove a draft proforma line (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int, required=True, help="Line id")

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        line = live_line(options["id"])
        proforma = line.proforma
        remove_line(line, user)
        return proforma_detail_payload(proforma)
