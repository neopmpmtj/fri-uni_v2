from proformas.agent_cli import (
    AgentCommand,
    live_get,
    serialize_item_detail,
    show_payload,
)
from proformas.models import Item


class Command(AgentCommand):
    help = "Show one live catalog item (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle_payload(self, **options):
        item = live_get(Item, options["id"], entity="item")
        item = Item.objects.select_related(
            "power", "brand", "sub_family__family", "vat_rate"
        ).get(pk=item.pk)
        return show_payload("item", serialize_item_detail(item))
