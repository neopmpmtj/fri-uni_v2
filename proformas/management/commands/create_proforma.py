from decimal import Decimal, InvalidOperation

from django.core.management.base import CommandError
from django.db import transaction

from proformas.agent_cli import (
    AgentCommand,
    add_cli_lines,
    add_user_argument,
    live_get,
    parse_volume,
    proforma_detail_payload,
    resolve_user,
)
from proformas.models import Site, TubingLength
from proformas.services import add_default_split, create_draft, issue_proforma


class Command(AgentCommand):
    help = "Create a proforma using the same services as the staff website (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        parser.add_argument("--site", type=int, required=True, help="Site id")
        parser.add_argument(
            "--line",
            action="append",
            dest="lines",
            help="item_id:qty or item_id:qty:tubing_length_id",
        )
        parser.add_argument("--volume-m3", dest="volume_m3", default="")
        parser.add_argument("--tubing", type=int)
        parser.add_argument("--discount-percent", default=None)
        parser.add_argument("--commercial-discount-percent", default=None)
        parser.add_argument("--validity-days", default=None)
        parser.add_argument("--extra-labour", default=None)
        parser.add_argument("--observations", default="")
        parser.add_argument("--issue", action="store_true")

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        site = live_get(Site, options["site"], entity="site")
        volume_raw = (options.get("volume_m3") or "").strip()
        lines = options.get("lines") or []
        if bool(volume_raw) == bool(lines):
            raise CommandError(
                "Provide --volume-m3 or at least one --line, not both."
            )
        if options.get("tubing") is not None and not volume_raw:
            raise CommandError("--tubing is only valid with --volume-m3.")

        draft_kwargs = {"observations": options["observations"] or ""}
        try:
            if options["discount_percent"] is not None:
                draft_kwargs["discount_percent"] = Decimal(
                    str(options["discount_percent"])
                )
            if options["commercial_discount_percent"] is not None:
                draft_kwargs["commercial_discount_percent"] = Decimal(
                    str(options["commercial_discount_percent"])
                )
            if options["validity_days"] is not None:
                draft_kwargs["validity_days"] = options["validity_days"]
            if options["extra_labour"] is not None:
                draft_kwargs["extra_labour"] = Decimal(str(options["extra_labour"]))
        except (InvalidOperation, TypeError) as exc:
            raise CommandError("Invalid discount percent or extra labour.") from exc

        with transaction.atomic():
            proforma = create_draft(site, user, **draft_kwargs)
            if volume_raw:
                tubing = None
                extra = False
                if options.get("tubing") is not None:
                    tubing = live_get(
                        TubingLength, options["tubing"], entity="tubing length"
                    )
                    extra = True
                add_default_split(
                    proforma,
                    parse_volume(volume_raw),
                    user,
                    extra_tubing=extra,
                    tubing_length=tubing,
                )
            else:
                add_cli_lines(proforma, user, lines)
            if options["issue"]:
                issue_proforma(proforma, user)
        return proforma_detail_payload(proforma)
