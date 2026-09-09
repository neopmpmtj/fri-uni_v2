from django.core.management.base import BaseCommand

from proformas.seed import (
    AGENT_ADMIN_EMAIL,
    AGENT_EMAIL,
    DEMO_ADMIN_EMAIL,
    DEMO_MANAGER_EMAIL,
    DEMO_PASSWORD,
    seed_demo,
)


class Command(BaseCommand):
    help = (
        "Idempotent demo suite: catalog, admin and manager users, "
        "agent badges, clients, sites, and sample proformas. Local only."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help=f"Password for demo users (default {DEMO_PASSWORD}).",
        )
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Reset demo user passwords if the accounts already exist.",
        )

    def handle(self, *args, **options):
        seed_demo(
            password=options["password"],
            reset_password=options["reset_password"],
        )
        self.stdout.write("Demo seed complete.")
        self.stdout.write(f"  admin:   {DEMO_ADMIN_EMAIL}  (Django admin, can delete)")
        self.stdout.write(
            f"  manager: {DEMO_MANAGER_EMAIL}  (staff UI, cannot delete)"
        )
        self.stdout.write(f"  agent:   {AGENT_EMAIL}  (Pi quoting, cannot delete)")
        self.stdout.write(
            f"  agent-admin: {AGENT_ADMIN_EMAIL}  (Pi deletes after confirm)"
        )
        self.stdout.write(f"  password: {options['password']}")
