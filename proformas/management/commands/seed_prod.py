from django.core.management.base import BaseCommand

from proformas.seed import (
    AGENT_ADMIN_EMAIL,
    AGENT_ADMIN_PASSWORD_ENV,
    AGENT_EMAIL,
    AGENT_PASSWORD_ENV,
    resolve_agent_passwords,
    seed_prod,
)


class Command(BaseCommand):
    help = (
        "Idempotent production seed: agent@ (staff) and agent-admin@ (admin). "
        "No demo clients or quotes. Passwords from .env or flags."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=None,
            help=f"Password for {AGENT_EMAIL} (else {AGENT_PASSWORD_ENV}).",
        )
        parser.add_argument(
            "--admin-password",
            default=None,
            help=f"Password for {AGENT_ADMIN_EMAIL} (else {AGENT_ADMIN_PASSWORD_ENV}).",
        )
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Reset agent passwords if the accounts already exist.",
        )

    def handle(self, *args, **options):
        staff_password, admin_password = resolve_agent_passwords(
            staff_password=options["password"],
            admin_password=options["admin_password"],
        )
        seed_prod(
            staff_password=staff_password,
            admin_password=admin_password,
            reset_password=options["reset_password"],
        )
        self.stdout.write("Production agent users ready.")
        self.stdout.write(f"  staff:  {AGENT_EMAIL}  (quoting CLI, cannot delete)")
        self.stdout.write(
            f"  admin:  {AGENT_ADMIN_EMAIL}  (Django admin, can delete)"
        )
        self.stdout.write("  passwords: set (not printed)")
