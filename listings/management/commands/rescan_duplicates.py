from django.core.management.base import BaseCommand

from listings import duplicates
from listings.models import Listing


class Command(BaseCommand):
    help = "Re-run rule-based duplicate/fake-listing detection against listings."

    def add_arguments(self, parser):
        parser.add_argument("--listing-id", type=int, default=None)

    def handle(self, *args, **options):
        listing_id = options["listing_id"]
        if listing_id:
            queryset = Listing.objects.filter(pk=listing_id)
        else:
            queryset = None

        summary = duplicates.rescan_all(queryset)
        self.stdout.write(
            self.style.SUCCESS(
                f"Scanned {summary['scanned']} listings, "
                f"created {summary['flags_created']} flags."
            )
        )
