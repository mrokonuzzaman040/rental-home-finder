"""Shared listing queryset helpers for browse/search ordering and filters."""

from django.db.models import Case, IntegerField, Q, When


def filter_by_tenant(qs, tenant_key: str | None):
    """tenant_key: 'bachelor', 'family', 'girl', or None; include compatible Any."""
    # Use DB string values explicitly (avoids TextChoices comparison quirks).
    if tenant_key == "bachelor":
        return qs.filter(Q(tenant_type="bachelor") | Q(tenant_type="any"))
    if tenant_key == "family":
        return qs.filter(Q(tenant_type="family") | Q(tenant_type="any"))
    if tenant_key == "girl":
        return qs.filter(Q(tenant_type="girl") | Q(tenant_type="any"))
    return qs


def order_city_first(qs, city: str | None):
    """Listings matching city (case-insensitive) appear first, then by newest."""
    if not (city or "").strip():
        return qs.order_by("-list_date")
    c = city.strip()
    return qs.annotate(
        _near_you=Case(
            When(city__iexact=c, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("_near_you", "-list_date")
