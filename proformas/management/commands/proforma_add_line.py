from proformas.agent_cli import (
    AgentCommand,
    add_proforma_argument,
    add_user_argument,
    live_get,
    live_line,
    proforma_detail_payload,
    resolve_user,
)
from proformas.models import Item, Proforma, TubingLength
from proformas.services import add_line


class Command(AgentCommand):
    help = "Add a line to a draft proforma (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        add_proforma_argument(parser)
        parser.add_argument("--item", type=int, required=True)
        parser.add_argument("--qty", type=int, default=1)
        parser.add_argument("--parent", type=int)
        parser.add_argument("--tubing", type=int)

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        proforma = live_get(Proforma, options["proforma"], entity="proforma")
        item = live_get(Item, options["item"], entity="item")
        parent = None
        if options.get("parent") is not None:
            parent = live_line(options["parent"])
        tubing = None
        extra = False
        if options.get("tubing") is not None:
            tubing = live_get(TubingLength, options["tubing"], entity="tubing length")
            extra = True
        add_line(
            proforma,
            item,
            user,
            quantity=options["qty"],
            extra_tubing=extra,
            tubing_length=tubing,
            parent_line=parent,
        )
        return proforma_detail_payload(proforma)
