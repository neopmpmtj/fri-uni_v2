from django.core.management.base import CommandError

from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_get,
    live_line,
    proforma_detail_payload,
    resolve_user,
)
from proformas.models import Item, TubingLength
from proformas.services import update_line


class Command(AgentCommand):
    help = "Update a draft proforma line (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int, required=True, help="Line id")
        parser.add_argument("--item", type=int)
        parser.add_argument("--qty", type=int)
        parser.add_argument("--parent", type=int)
        parser.add_argument("--tubing", type=int)
        parser.add_argument("--no-tubing", action="store_true")

    def handle_payload(self, **options):
        if options.get("tubing") is not None and options.get("no_tubing"):
            raise CommandError("Use --tubing or --no-tubing, not both.")
        user = resolve_user(options["user"])
        line = live_line(options["id"])
        kwargs = {}
        if options.get("item") is not None:
            kwargs["item"] = live_get(Item, options["item"], entity="item")
        if options.get("qty") is not None:
            kwargs["quantity"] = options["qty"]
        if options.get("parent") is not None:
            kwargs["parent_line"] = live_line(options["parent"])
        if options.get("no_tubing"):
            kwargs["extra_tubing"] = False
        elif options.get("tubing") is not None:
            kwargs["extra_tubing"] = True
            kwargs["tubing_length"] = live_get(
                TubingLength, options["tubing"], entity="tubing length"
            )
        update_line(line, user, **kwargs)
        return proforma_detail_payload(line.proforma)
