from pathlib import Path

from accounts.lang import normalize_lang
from proformas.agent_cli import (
    AgentCommand,
    add_proforma_argument,
    add_user_argument,
    live_get,
    require_issued,
    resolve_user,
    show_payload,
)
from proformas.models import Proforma
from proformas.pdf import build_proforma_pdf
from proformas.services import log_activity


class Command(AgentCommand):
    help = "Write an issued proforma PDF to a file (JSON)."

    def add_arguments(self, parser):
        add_user_argument(parser)
        add_proforma_argument(parser)
        parser.add_argument("--out", required=True, help="Output file path")
        parser.add_argument("--lang", default="en")

    def handle_payload(self, **options):
        user = resolve_user(options["user"])
        proforma = require_issued(
            live_get(Proforma, options["proforma"], entity="proforma")
        )
        lang = normalize_lang(options.get("lang") or "en")
        pdf_bytes = build_proforma_pdf(proforma, lang=lang)
        path = Path(options["out"]).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)
        log_activity(
            action="download_pdf",
            object_type="proforma",
            object_id=proforma.pk,
            actor=user,
        )
        return show_payload(
            "proforma",
            {
                "id": proforma.pk,
                "number": proforma.number,
                "path": str(path.resolve()),
                "bytes": len(pdf_bytes),
            },
        )
