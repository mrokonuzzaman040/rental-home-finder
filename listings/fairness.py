"""Rent Fairness Estimator - prototype comparator, not an official rent index.

Compares a listing's rent against similar listings (same city + bedroom count,
tenant-type compatible). Falls back to a city-only average when the sample is
too small to be meaningful.
"""

from django.db.models import Avg, Q

MIN_SAMPLE_SIZE = 5


def comparable_queryset(listing):
    from .models import Listing

    return (
        Listing.objects.filter(
            city=listing.city, bedrooms=listing.bedrooms, is_published=True
        )
        .filter(Q(tenant_type=listing.tenant_type) | Q(tenant_type="any"))
        .exclude(pk=listing.pk)
    )


def rent_fairness(listing) -> dict:
    from .models import Listing

    comp_qs = comparable_queryset(listing)
    comparable_count = comp_qs.count()
    scope = "area"

    if comparable_count < MIN_SAMPLE_SIZE:
        comp_qs = Listing.objects.filter(city=listing.city, is_published=True).exclude(
            pk=listing.pk
        )
        comparable_count = comp_qs.count()
        scope = "city"

    avg_price = comp_qs.aggregate(Avg("price"))["price__avg"]

    label = "Not enough data to compare"
    color = "text-muted"
    diff_percent = None

    if avg_price:
        diff_percent = ((float(listing.price) - float(avg_price)) / float(avg_price)) * 100
        if diff_percent < -10:
            label = "Great deal - below similar listings"
            color = "text-success"
        elif diff_percent > 15:
            label = f"High rent - about {diff_percent:.0f}% above similar listings"
            color = "text-danger"
        else:
            label = "Fair price - close to similar listings"
            color = "text-dark"

    return {
        "comparable_count": comparable_count,
        "avg_price": avg_price,
        "diff_percent": diff_percent,
        "label": label,
        "color": color,
        "scope": scope,
        "is_prototype": True,
    }
