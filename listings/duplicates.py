"""Rule-based fake/duplicate listing detection (no ML, no image-similarity model).

5 rules per the thesis spec:
  1. Same phone number reused across many listings
  2. Same address, different rents
  3. Very low rent for an otherwise-expensive area
  4. Very similar title/description text
  5. Repeated image (same file hash) across listings
"""

import difflib
import hashlib

from django.db.models import Avg

PHONE_REUSE_THRESHOLD = 3
ADDRESS_PRICE_MIN_DIFF_PCT = 10.0
LOW_RENT_THRESHOLD_PCT = 40.0
TEXT_SIMILARITY_CUTOFF = 0.85
TEXT_SIMILARITY_SCOPE_LIMIT = 300


def hash_uploaded_file(uploaded_file) -> str:
    """MD5 hash of an uploaded/opened file's bytes, used for the repeated-image rule."""
    hasher = hashlib.md5()
    if hasattr(uploaded_file, "chunks"):
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
    else:
        uploaded_file.seek(0)
        hasher.update(uploaded_file.read())
    uploaded_file.seek(0)
    return hasher.hexdigest()


def rule_phone_reuse(listing):
    from .models import Listing, ListingFlag

    if not listing.contact_phone:
        return []
    others = Listing.objects.filter(contact_phone=listing.contact_phone).exclude(
        pk=listing.pk
    )
    count = others.count()
    if count + 1 < PHONE_REUSE_THRESHOLD:
        return []
    return [
        ListingFlag(
            listing=listing,
            rule=ListingFlag.Rule.PHONE_REUSE,
            detail=f"Phone {listing.contact_phone} used on {count + 1} listings.",
            score=min(100, (count + 1) * 10),
        )
    ]


def rule_address_price_mismatch(listing):
    from .models import Listing, ListingFlag

    if not listing.address:
        return []
    others = Listing.objects.filter(address__iexact=listing.address).exclude(
        pk=listing.pk
    )
    flags = []
    for other in others:
        if not other.price:
            continue
        diff_pct = abs(float(listing.price) - float(other.price)) / float(other.price) * 100
        if diff_pct >= ADDRESS_PRICE_MIN_DIFF_PCT:
            flags.append(
                ListingFlag(
                    listing=listing,
                    related_listing=other,
                    rule=ListingFlag.Rule.ADDRESS_PRICE_MISMATCH,
                    detail=(
                        f"Same address listed at ৳{listing.price} here vs "
                        f"৳{other.price} on listing #{other.pk}."
                    ),
                    score=min(100, int(diff_pct)),
                )
            )
    return flags


def rule_low_rent_for_area(listing):
    from .models import Listing, ListingFlag

    avg_price = (
        Listing.objects.filter(city=listing.city)
        .exclude(pk=listing.pk)
        .aggregate(Avg("price"))["price__avg"]
    )
    if not avg_price:
        return []
    threshold = float(avg_price) * (1 - LOW_RENT_THRESHOLD_PCT / 100)
    if float(listing.price) >= threshold:
        return []
    return [
        ListingFlag(
            listing=listing,
            rule=ListingFlag.Rule.LOW_RENT_AREA,
            detail=(
                f"Rent ৳{listing.price} is far below the {listing.city} "
                f"average of ৳{avg_price:.0f}."
            ),
            score=80,
        )
    ]


def rule_text_similarity(listing):
    from .models import Listing, ListingFlag

    candidates = (
        Listing.objects.filter(city=listing.city)
        .exclude(pk=listing.pk)
        .order_by("-list_date")[:TEXT_SIMILARITY_SCOPE_LIMIT]
    )
    this_text = f"{listing.title} {listing.description}"
    flags = []
    for other in candidates:
        other_text = f"{other.title} {other.description}"
        ratio = difflib.SequenceMatcher(None, this_text, other_text).ratio()
        if ratio >= TEXT_SIMILARITY_CUTOFF:
            flags.append(
                ListingFlag(
                    listing=listing,
                    related_listing=other,
                    rule=ListingFlag.Rule.TEXT_SIMILARITY,
                    detail=f"{ratio * 100:.0f}% similar to listing #{other.pk}.",
                    score=int(ratio * 100),
                )
            )
    return flags


def rule_image_reuse(listing):
    from .models import Listing, ListingFlag

    if not listing.main_image_hash:
        return []
    others = Listing.objects.filter(main_image_hash=listing.main_image_hash).exclude(
        pk=listing.pk
    )
    flags = []
    for other in others:
        flags.append(
            ListingFlag(
                listing=listing,
                related_listing=other,
                rule=ListingFlag.Rule.IMAGE_REUSE,
                detail=f"Same main photo as listing #{other.pk}.",
                score=90,
            )
        )
    return flags


def scan_listing(listing):
    flags = []
    flags += rule_phone_reuse(listing)
    flags += rule_address_price_mismatch(listing)
    flags += rule_low_rent_for_area(listing)
    flags += rule_text_similarity(listing)
    flags += rule_image_reuse(listing)
    return flags


def apply_flags(listing, flags):
    from .models import ListingFlag

    ListingFlag.objects.filter(listing=listing, resolved=False).delete()
    if flags:
        ListingFlag.objects.bulk_create(flags)


def rescan_all(queryset=None) -> dict:
    from .models import Listing

    if queryset is None:
        queryset = Listing.objects.filter(is_published=True)

    scanned = 0
    flags_created = 0
    for listing in queryset:
        flags = scan_listing(listing)
        apply_flags(listing, flags)
        scanned += 1
        flags_created += len(flags)
    return {"scanned": scanned, "flags_created": flags_created}
