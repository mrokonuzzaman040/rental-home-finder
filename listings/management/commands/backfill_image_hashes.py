from django.core.management.base import BaseCommand

from listings import duplicates
from listings.models import Listing, ListingImage


class Command(BaseCommand):
    help = "Compute main_image_hash / image_hash for existing listing images."

    def handle(self, *args, **options):
        updated = 0
        for listing in Listing.objects.exclude(main_image="").exclude(
            main_image_hash__gt=""
        ):
            try:
                listing.main_image_hash = duplicates.hash_uploaded_file(
                    listing.main_image
                )
                listing.save(update_fields=["main_image_hash"])
                updated += 1
            except (FileNotFoundError, ValueError):
                continue

        for image in ListingImage.objects.exclude(image_hash__gt=""):
            try:
                image.image_hash = duplicates.hash_uploaded_file(image.image)
                image.save(update_fields=["image_hash"])
                updated += 1
            except (FileNotFoundError, ValueError):
                continue

        self.stdout.write(self.style.SUCCESS(f"Hashed {updated} images."))
