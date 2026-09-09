from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_get,
    model_form_data,
    overlay_options,
    resolve_user,
    run_form_save,
    serialize_client_detail,
    show_payload,
)
from proformas.forms import ClientForm
from proformas.models import Client
from proformas.services import save_client

CLIENT_OPTIONS = {
    "kind": "kind",
    "name": "name",
    "nif": "tax_number",
    "street": "street",
    "postal_code": "postal_code",
    "city": "city",
    "phone": "phone",
    "email": "email",
    "contact_name": "contact_name",
    "contact_position": "contact_position",
}


class Command(AgentCommand):
    help = "Create or update a client via save_client (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int)
        parser.add_argument("--kind", choices=["person", "company"])
        parser.add_argument("--name")
        parser.add_argument("--nif")
        parser.add_argument("--street")
        parser.add_argument("--postal-code")
        parser.add_argument("--city")
        parser.add_argument("--phone")
        parser.add_argument("--email")
        parser.add_argument("--contact-name")
        parser.add_argument("--contact-position", type=int)

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        instance = None
        if options.get("id") is not None:
            instance = live_get(Client, options["id"], entity="client")
            data = model_form_data(instance, ClientForm.Meta.fields)
        else:
            data = {}
            data["kind"] = Client.Kind.PERSON
            data["country_code"] = "PT"
        overlay_options(data, options, CLIENT_OPTIONS)
        client = run_form_save(
            form_class=ClientForm,
            data=data,
            user=user,
            instance=instance,
            save_fn=save_client,
        )
        return show_payload("client", serialize_client_detail(client))
