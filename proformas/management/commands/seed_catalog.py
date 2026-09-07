from django.core.management.base import BaseCommand

from proformas.seed import seed_catalog


class Command(BaseCommand):
    help = "Idempotent demo catalog: brands, styles, models, tubing, parameters."

    def handle(self, *args, **options):
        seed_catalog()
        self.stdout.write("Catalog seed complete.")
        self.stdout.write("For a clickable demo (users, clients, quotes), run: seed_demo")
