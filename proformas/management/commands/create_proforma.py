from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from proformas.models import Item, Site, TubingLength
from proformas.services import add_line, create_draft, issue_proforma


def _command_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(str(message) for message in exc.messages)
    return str(exc)


class Command(BaseCommand):
    help = "Create a proforma using the same services as the staff website."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Staff email (created_by)")
        parser.add_argument("--site", type=int, required=True, help="Site id")
        parser.add_argument(
            "--line",
            action="append",
            required=True,
            help="item_id:qty or item_id:qty:tubing_length_id",
        )
        parser.add_argument("--discount-percent", default=None)
        parser.add_argument("--extra-labour", default=None)
        parser.add_argument("--observations", default="")
        parser.add_argument("--issue", action="store_true")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(email=options["user"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Unknown user {options['user']}") from exc
        if not user.is_active:
            raise CommandError(f"Inactive user {options['user']}")
        try:
            site = Site.objects.get(pk=options["site"])
        except Site.DoesNotExist as exc:
            raise CommandError(f"Unknown site {options['site']}") from exc

        draft_kwargs = {"observations": options["observations"] or ""}
        try:
            if options["discount_percent"] is not None:
                draft_kwargs["discount_percent"] = Decimal(
                    str(options["discount_percent"])
                )
            if options["extra_labour"] is not None:
                draft_kwargs["extra_labour"] = Decimal(str(options["extra_labour"]))
        except (InvalidOperation, TypeError) as exc:
            raise CommandError("Invalid discount percent or extra labour.") from exc

        try:
            with transaction.atomic():
                proforma = create_draft(site, user, **draft_kwargs)
                for spec in options["line"]:
                    parts = spec.split(":")
                    if len(parts) not in (2, 3):
                        raise CommandError(
                            "Each --line must be item_id:qty or "
                            "item_id:qty:tubing_length_id"
                        )
                    try:
                        item_id = int(parts[0])
                        quantity = int(parts[1])
                    except ValueError as exc:
                        raise CommandError(
                            "Each --line must be item_id:qty or "
                            "item_id:qty:tubing_length_id"
                        ) from exc
                    try:
                        item = Item.objects.get(pk=item_id)
                    except Item.DoesNotExist as exc:
                        raise CommandError(f"Unknown item {parts[0]}") from exc
                    tubing = None
                    extra = False
                    if len(parts) == 3:
                        try:
                            tubing_id = int(parts[2])
                        except ValueError as exc:
                            raise CommandError(
                                "Each --line must be item_id:qty or "
                                "item_id:qty:tubing_length_id"
                            ) from exc
                        try:
                            tubing = TubingLength.objects.get(pk=tubing_id)
                        except TubingLength.DoesNotExist as exc:
                            raise CommandError(
                                f"Unknown tubing length {parts[2]}"
                            ) from exc
                        extra = True
                    add_line(
                        proforma,
                        item,
                        user,
                        quantity=quantity,
                        extra_tubing=extra,
                        tubing_length=tubing,
                    )
                if options["issue"]:
                    issue_proforma(proforma, user)
        except ValidationError as exc:
            raise CommandError(_command_message(exc)) from exc

        proforma.refresh_from_db()
        self.stdout.write(proforma.number)
