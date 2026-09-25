"""Smart Match Score - rule-based, explainable ranking (not ML).

Match Score = Budget Fit + Location Fit + Tenant Fit + Verification Score + Feature Match
"""

# Max points per component (tune freely). Sums to 100.
WEIGHT_BUDGET = 30
WEIGHT_LOCATION = 20
WEIGHT_TENANT = 20
WEIGHT_VERIFICATION = 15
WEIGHT_FEATURE = 15


def budget_fit_score(price, budget) -> int:
    if not budget:
        return WEIGHT_BUDGET
    price = float(price)
    budget = float(budget)
    if budget <= 0:
        return WEIGHT_BUDGET
    diff_ratio = abs(price - budget) / budget
    if diff_ratio <= 0.1:
        return WEIGHT_BUDGET
    if diff_ratio <= 0.2:
        return int(WEIGHT_BUDGET * 0.7)
    if diff_ratio <= 0.4:
        return int(WEIGHT_BUDGET * 0.35)
    return 0


def location_fit_score(listing, preferred_city, preferred_area=None) -> int:
    if not preferred_city:
        return WEIGHT_LOCATION
    if listing.city.lower() != preferred_city.lower():
        return 0
    if preferred_area and preferred_area.lower() not in (listing.address or "").lower():
        return int(WEIGHT_LOCATION * 0.6)
    return WEIGHT_LOCATION


def tenant_fit_score(listing_tenant_type, tenant_key=None) -> int:
    if not tenant_key:
        return WEIGHT_TENANT
    if listing_tenant_type == "any" or listing_tenant_type == tenant_key:
        return WEIGHT_TENANT
    return 0


def verification_score(listing) -> int:
    return round((listing.trust_score / 100) * WEIGHT_VERIFICATION)


def feature_match_score(listing, priority=None, bedrooms_min=None, bedrooms_max=None) -> int:
    score = WEIGHT_FEATURE if not priority else 0
    if priority == "space" and listing.square_feet > 1500:
        score = WEIGHT_FEATURE
    elif priority == "luxury" and listing.is_furnished:
        score = WEIGHT_FEATURE
    elif priority == "price":
        score = WEIGHT_FEATURE
    elif priority:
        score = int(WEIGHT_FEATURE * 0.4)

    if bedrooms_min is not None and listing.bedrooms < bedrooms_min:
        score = int(score * 0.5)
    if bedrooms_max is not None and listing.bedrooms > bedrooms_max:
        score = int(score * 0.5)
    return score


def match_score(
    listing,
    *,
    city=None,
    budget=None,
    tenant=None,
    priority=None,
    preferred_area=None,
    bedrooms_min=None,
    bedrooms_max=None,
) -> dict:
    breakdown = {
        "budget": budget_fit_score(listing.price, budget),
        "location": location_fit_score(listing, city, preferred_area),
        "tenant": tenant_fit_score(listing.tenant_type, tenant),
        "verification": verification_score(listing),
        "feature": feature_match_score(listing, priority, bedrooms_min, bedrooms_max),
    }
    return {"total": sum(breakdown.values()), "breakdown": breakdown}


def rank_listings(queryset, **criteria) -> list:
    """Returns a list of {"listing", "total", "breakdown"} sorted best-match first."""
    ranked = [
        {"listing": item, **match_score(item, **criteria)} for item in queryset
    ]
    ranked.sort(key=lambda row: row["total"], reverse=True)
    return ranked
