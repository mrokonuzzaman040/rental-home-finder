"""Verified Listing Trust Score - rule-based, computed from admin verification fields."""

# Points per verification item (tune freely). Sums to 100.
TRUST_WEIGHTS = {
    "phone_verified": 15,
    "address_verified": 20,
    "photos_verified": 15,
    "rent_confirmed": 15,
    "availability_confirmed": 10,
    "document_checked": 15,
    "no_previous_complaint": 10,
}


def _has_open_complaint(listing) -> bool:
    if not listing.pk:
        return False
    from .models import Complaint

    return (
        Complaint.objects.filter(listing=listing)
        .exclude(status=Complaint.Status.REJECTED)
        .exists()
    )


def compute_trust_score(listing) -> int:
    score = 0
    for field, weight in TRUST_WEIGHTS.items():
        if field == "no_previous_complaint":
            if not _has_open_complaint(listing):
                score += weight
        elif getattr(listing, field, False):
            score += weight
    return score


def recompute_and_save(listing) -> int:
    listing.trust_score = compute_trust_score(listing)
    listing.save(update_fields=["trust_score"])
    return listing.trust_score


def trust_label(score: int) -> tuple[str, str]:
    """Returns (label, bootstrap color class)."""
    if score >= 85:
        return "Verified by Admin", "success"
    if score >= 50:
        return "Partially Verified", "warning"
    return "Unverified", "secondary"
