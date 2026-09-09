from proformas.agent_cli import (
    AgentCommand,
    add_proforma_argument,
    add_user_argument,
    live_get,
    proforma_detail_payload,
    resolve_user,
)
from proformas.models import Proforma
from proformas.services import unaccept_proforma


class Command(AgentCommand):
    help = "Clear the accepted overlay on an issued proforma (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        add_proforma_argument(parser)

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        proforma = live_get(Proforma, options["proforma"], entity="proforma")
        return proforma_detail_payload(unaccept_proforma(proforma, user))
