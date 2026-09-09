from proformas.agent_cli import (
    AgentCommand,
    add_user_argument,
    live_get,
    model_form_data,
    overlay_options,
    resolve_user,
    run_form_save,
    serialize_site_detail,
    show_payload,
)
from proformas.forms import SiteForm
from proformas.models import Site
from proformas.services import save_audited

SITE_OPTIONS = {
    "client": "client",
    "alias_1": "alias_1",
    "alias_2": "alias_2",
    "alias_3": "alias_3",
    "alias_4": "alias_4",
    "street": "street",
    "postal_code": "postal_code",
    "city": "city",
    "phone": "phone",
    "email": "email",
    "contact_name": "contact_name",
    "contact_position": "contact_position",
    "notes": "notes",
}


class Command(AgentCommand):
    help = "Create or update a site via save_audited (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--id", type=int)
        parser.add_argument("--client", type=int)
        parser.add_argument("--alias-1")
        parser.add_argument("--alias-2")
        parser.add_argument("--alias-3")
        parser.add_argument("--alias-4")
        parser.add_argument("--street")
        parser.add_argument("--postal-code")
        parser.add_argument("--city")
        parser.add_argument("--phone")
        parser.add_argument("--email")
        parser.add_argument("--contact-name")
        parser.add_argument("--contact-position", type=int)
        parser.add_argument("--notes")

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        instance = None
        if options.get("id") is not None:
            instance = live_get(Site, options["id"], entity="site")
            data = model_form_data(instance, SiteForm.Meta.fields)
        else:
            data = {}
        overlay_options(data, options, SITE_OPTIONS)
        site = run_form_save(
            form_class=SiteForm,
            data=data,
            user=user,
            instance=instance,
            save_fn=save_audited,
        )
        site = Site.objects.select_related("client").get(pk=site.pk)
        return show_payload("site", serialize_site_detail(site))
