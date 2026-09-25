from django.conf import settings

from .choices import BANGLADESH_CITY_CHOICES, TENANT_FILTER_VALUES
from .models import Listing
from .rewards import wallet_summary

_FALLBACK_MODAL_CITIES = [city for city, _label in BANGLADESH_CITY_CHOICES]


def visitor_location(request):
    """First-visit location modal on home + session preferences site-wide."""
    is_home = getattr(request.resolver_match, "url_name", None) == "listings"
    show_modal = not request.session.get("rf_location_prompt_done") and is_home
    modal_cities = []
    if show_modal:
        modal_cities = list(
            Listing.objects.filter(is_published=True)
            .values_list("city", flat=True)
            .distinct()
            .order_by("city")
        )
        if not modal_cities:
            modal_cities = list(_FALLBACK_MODAL_CITIES)

    # Align chip UI with URL (?tenant=) first, then session (pagination).
    tenant_display = ""
    if "tenant" in request.GET:
        tv = (request.GET.get("tenant") or "").strip().lower()
        if tv in TENANT_FILTER_VALUES:
            tenant_display = tv
    if not tenant_display:
        tenant_display = request.session.get("preferred_tenant") or ""

    return {
        "show_location_modal": show_modal,
        "modal_city_choices": modal_cities,
        "visitor_city": (request.session.get("preferred_city") or "").strip(),
        "visitor_tenant": tenant_display,
    }


def reward_nav(request):
    if request.user.is_authenticated:
        return {"reward_nav": wallet_summary(request.user)}
    return {"reward_nav": None}


def assistant_limits(request):
    guest_cap = getattr(settings, "AI_ASSISTANT_GUEST_MESSAGE_CAP", 5)
    user_cap = getattr(settings, "AI_ASSISTANT_USER_DAILY_CAP", 100)
    if request.user.is_authenticated:
        from django.utils import timezone

        from .models import AiAssistantDailyUsage

        today = timezone.localdate()
        row = AiAssistantDailyUsage.objects.filter(user=request.user, day=today).first()
        used = row.count if row else 0
        rem = max(0, user_cap - used)
        return {"assistant_remaining": rem, "assistant_limit": user_cap}
    used = request.session.get("ai_assistant_guest_count", 0)
    rem = max(0, guest_cap - used)
    return {"assistant_remaining": rem, "assistant_limit": guest_cap}
