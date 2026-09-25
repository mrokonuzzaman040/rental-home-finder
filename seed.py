"""
Populate the database with demo listings (default: 100).

Usage:
  python seed.py           # replaces all listings with 100 seed rows
  python seed.py --append  # add 100 listings without deleting existing

Requires a user named 'admin' (creates one with password 'admin123' if missing).
"""

import argparse
import os
import random
import sys

import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User
from listings.models import Listing
from listings import trust_score as trust_score_module

# Reproducible variety
random.seed(42)

CITIES_AREAS = [
    (
        "Dhaka",
        [
            "Gulshan 2",
            "Banani",
            "Dhanmondi",
            "Uttara",
            "Mirpur",
            "Mohammadpur",
            "Baridhara",
            "Bashundhara",
            "Farmgate",
            "Tejgaon",
            "Khilgaon",
            "Rampura",
        ],
    ),
    (
        "Chittagong",
        ["Nasirabad", "Panchlaish", "Agrabad", "Halishahar", "Khulshi", "Bayezid"],
    ),
    ("Sylhet", ["Zindabazar", "Ambarkhana", "Shibgonj", "Subidbazar"]),
    ("Rajshahi", ["Shaheb Bazar", "Boalia", "Talaimari"]),
    ("Khulna", ["Sonadanga", "Khalishpur", "Daulatpur"]),
    ("Gazipur", ["Joydebpur", "Konabari", "Tongi"]),
    ("Mymensingh", ["Charpara", "Kachari"]),
]

ADJECTIVES = [
    "Modern",
    "Spacious",
    "Cozy",
    "Bright",
    "Renovated",
    "Premium",
    "Quiet",
    "Family-friendly",
    "Sunlit",
    "Well-maintained",
    "Stylish",
    "Comfortable",
    "Executive",
    "Affordable",
    "Lake-view",
    "Garden-facing",
    "Corner unit",
]

HOME_TYPES = [
    "Apartment",
    "Flat",
    "Duplex",
    "Studio",
    "Penthouse",
    "Floor",
    "Townhouse",
    "Family flat",
    "Rental unit",
    "Residential suite",
]

TENANT_FIT_NOTES = [
    "Suitable for female students, small family, and job holders. Not allowed: bachelor male group.",
    "Bachelor-friendly shared apartment near university. Not allowed: families with young children.",
    "Family-only flat in a quiet residential block. Not allowed: bachelor groups.",
    "Open to job holders and sublets. Female students welcome.",
    "",
    "",
]

# A handful of phone numbers reused across many listings, so the duplicate
# detection demo (phone_reuse rule) has something real to find.
_REUSED_PHONES = ["+8801700000001", "+8801700000002", "+8801700000003"]


def make_phone(index: int) -> str:
    if index % 17 == 0:
        return random.choice(_REUSED_PHONES)
    return f"+8801{random.randint(700000000, 999999999)}"


def ensure_admin_user():
    user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@rentalfinder.local",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created or not user.has_usable_password():
        user.set_password("admin123")
        user.save()
        if created:
            print("Created user admin / admin123")
    return user


def build_description(city: str, beds: int, furnished: bool, ac: bool) -> str:
    bits = [
        f"Located in {city}.",
        f"{beds}-bed layout suitable for singles or families.",
        (
            "Electricity load suitable for inverter AC."
            if ac
            else "Ceiling fans throughout."
        ),
        (
            "Semi-furnished with fittings."
            if not furnished
            else "Fully furnished with sofas, beds, and wardrobes."
        ),
        "Walking distance to markets and transport.",
        "Water supply and lift available where applicable.",
        "Contact for viewing appointments.",
    ]
    random.shuffle(bits)
    return " ".join(bits[: random.randint(4, 6)])


def make_listing(owner: User, index: int) -> Listing:
    city, areas = random.choice(CITIES_AREAS)
    area = random.choice(areas)
    adj = random.choice(ADJECTIVES)
    htype = random.choice(HOME_TYPES)
    title = f"{adj} {htype} - {area}, {city}"[:200]

    beds = random.choices([1, 2, 3, 4, 5], weights=[15, 25, 35, 20, 5])[0]
    baths = min(beds, random.randint(1, max(2, beds)))
    sqft = max(380, beds * random.randint(280, 420) + random.randint(-80, 120))
    garage = random.choices([0, 1, 2], weights=[55, 35, 10])[0]

    furnished = random.random() < 0.42
    ac = random.random() < 0.55
    heating = random.random() < 0.85

    base = {"Dhaka": 28000, "Chittagong": 22000, "Sylhet": 18000}.get(city, 15000)
    price = Decimal(
        str(
            max(
                8500,
                int(
                    base
                    + beds * random.randint(3500, 9500)
                    + random.randint(-4000, 12000)
                ),
            )
        )
    )

    road = random.randint(1, 140)
    address = f'Road {road}, Block {random.choice(["A", "B", "C", "G", "H"])}, {area}'[
        :255
    ]

    status = random.choices(["available", "pending", "rented"], weights=[78, 14, 8])[0]

    published = random.random() < 0.94
    verified = random.random() < 0.22
    views = random.randint(0, 890)

    tenant_type = random.choices(
        [
            Listing.TenantType.BACHELOR,
            Listing.TenantType.FAMILY,
            Listing.TenantType.ANY,
        ],
        weights=[30, 40, 30],
    )[0]

    phone_verified = random.random() < 0.55
    address_verified = random.random() < 0.45
    photos_verified = random.random() < 0.5
    rent_confirmed = random.random() < 0.5
    availability_confirmed = random.random() < 0.4
    document_checked = random.random() < 0.3

    listing = Listing(
        title=title,
        description=build_description(city, beds, furnished, ac),
        address=address,
        city=city,
        price=price,
        bedrooms=beds,
        bathrooms=baths,
        square_feet=sqft,
        garage=garage,
        is_furnished=furnished,
        has_ac=ac,
        has_heating=heating,
        status=status,
        is_published=published,
        owner=owner,
        views_count=views,
        is_verified=verified,
        tenant_type=tenant_type,
        contact_phone=make_phone(index),
        tenant_fit_note=random.choice(TENANT_FIT_NOTES),
        phone_verified=phone_verified,
        address_verified=address_verified,
        photos_verified=photos_verified,
        rent_confirmed=rent_confirmed,
        availability_confirmed=availability_confirmed,
        document_checked=document_checked,
    )
    # bulk_create() skips Listing.save(), so compute trust_score up front.
    listing.trust_score = trust_score_module.compute_trust_score(listing)
    return listing


def seed_data(count: int = 100, append: bool = False):
    owner = ensure_admin_user()

    if not append:
        n, _ = Listing.objects.all().delete()
        print(f"Removed existing listings (deleted {n} objects).")

    batch = [make_listing(owner, i) for i in range(count)]

    # A couple of intentional same-address / different-rent duplicates, so the
    # rule-based duplicate detector (address_price_mismatch rule) has real
    # examples to flag when `manage.py rescan_duplicates` runs.
    if count >= 5:
        dup_source = batch[0]
        dup = make_listing(owner, count)
        dup.address = dup_source.address
        dup.city = dup_source.city
        dup.price = dup_source.price * Decimal("1.6")
        batch.append(dup)

    Listing.objects.bulk_create(batch)

    print(f"Created {len(batch)} seed listings (owner=admin).")
    print(
        "Browse at / or /search - login admin / admin123 if you use the created account."
    )
    print("Run 'python manage.py rescan_duplicates' to populate demo duplicate flags.")


def main():
    parser = argparse.ArgumentParser(description="Seed Rental Finder demo data.")
    parser.add_argument(
        "--append", action="store_true", help="Keep existing listings and add more."
    )
    parser.add_argument(
        "-n", "--count", type=int, default=100, help="Number of listings (default 100)."
    )
    args = parser.parse_args()
    if args.count < 1 or args.count > 5000:
        print("Count must be between 1 and 5000.", file=sys.stderr)
        sys.exit(1)
    seed_data(count=args.count, append=args.append)


if __name__ == "__main__":
    main()
