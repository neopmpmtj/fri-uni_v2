from proformas.agent_cli import (
    AgentCommand,
    live_get,
    serialize_proforma_detail,
    show_payload,
)
from proformas.models import Proforma


class Command(AgentCommand):
    help = "Show one live proforma (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle_payload(self, **options):
        proforma = live_get(Proforma, options["id"], entity="proforma")
        proforma = Proforma.objects.select_related("site__client").get(pk=proforma.pk)
        return show_payload("proforma", serialize_proforma_detail(proforma))
