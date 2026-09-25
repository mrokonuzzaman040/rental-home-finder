"""
Management command wrapper around seed.py.

Usage:
  python manage.py seed_data               # 100 listings, replaces existing
  python manage.py seed_data --count 200   # custom count
  python manage.py seed_data --append      # keep existing and add more
"""

import sys
import os
from django.core.management.base import BaseCommand

# Allow importing seed.py from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


class Command(BaseCommand):
    help = "Seed the database with demo listing data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=100,
            help="Number of listings to create (default: 100).",
        )
        parser.add_argument(
            "--append", action="store_true",
            help="Keep existing listings and add more.",
        )

    def handle(self, *args, **options):
        # Import seed module after Django is set up
        import importlib.util, pathlib
        seed_path = pathlib.Path(__file__).resolve().parents[4] / "seed.py"
        spec = importlib.util.spec_from_file_location("seed", seed_path)
        seed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seed)

        count = options["count"]
        append = options["append"]

        self.stdout.write(f"Seeding {count} listings (append={append}) …")
        seed.seed_data(count=count, append=append)
        self.stdout.write(self.style.SUCCESS("Seeding complete."))
