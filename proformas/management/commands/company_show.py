from proformas.agent_cli import AgentCommand, serialize_company, show_payload
from proformas.services import get_company


class Command(AgentCommand):
    help = "Show the live issuer company profile (JSON)."

    def handle_payload(self, **options):
        return show_payload("company", serialize_company(get_company()))
