from decimal import Decimal
import json

from django.conf import settings as dj_settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponsePermanentRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError as FormValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from .models import (
    AiAssistantDailyUsage,
    Complaint,
    Listing,
    ListingImage,
    Inquiry,
    Favorite,
    Review,
    ListingOffer,
    PointsLedger,
    Profile,
)
from . import duplicates, fairness, matching, roles
from .decorators import role_required
from .rewards import (
    POINTS_FAVORITE,
    POINTS_INQUIRY,
    POINTS_NEW_LISTING,
    POINTS_REVIEW,
    POINTS_SIGNUP,
    grant_favorite_points,
    grant_inquiry_points,
    grant_new_listing_points,
    grant_review_points,
    grant_signup_bonus,
    tier_progress,
    wallet_summary,
)
from .choices import BANGLADESH_CITY_CHOICES, CITY_COORDINATES, TENANT_FILTER_VALUES
from .forms import ListingForm, RegisterForm, validate_listing_image_file
from .queryset import filter_by_tenant, order_city_first
from .geo import reverse_geocode_city
from .ai_utils import (
    assistant_chat_reply,
    generate_property_description,
    get_neighborhood_insight,
    get_living_cost_estimate,
)

from django.core.paginator import Paginator
from django.db.models import Count, Q


def _sync_tenant_from_query(request):
    """Persist ?tenant= from browse chips or search form into session."""
    if "tenant" not in request.GET:
        return
    t = (request.GET.get("tenant") or "").strip().lower()
    if t in ("all", ""):
        request.session.pop("preferred_tenant", None)
        request.session.modified = True
    elif t in TENANT_FILTER_VALUES:
        request.session["preferred_tenant"] = t
        request.session.modified = True


def _active_tenant(request):
    """
    Effective tenant filter for ORM.
    Prefer the URL (?tenant=bachelor|family|girl|all) so results always match the address bar.
    If absent (e.g. ?page=2 only), reuse session set by chips or modal.
    """
    if "tenant" in request.GET:
        t = (request.GET.get("tenant") or "").strip().lower()
        if t in ("all", ""):
            return None
        if t in TENANT_FILTER_VALUES:
            return t
        return None
    sess = request.session.get("preferred_tenant")
    return sess if sess in TENANT_FILTER_VALUES else None


def _map_points_for_listings(listings):
    city_offsets = {}
    points = []
    for listing in listings:
        coords = CITY_COORDINATES.get(listing.city)
        if not coords:
            continue
        offset_index = city_offsets.get(listing.city, 0)
        city_offsets[listing.city] = offset_index + 1
        lat, lon = coords
        spread = (offset_index % 7) * 0.006
        points.append(
            {
                "title": listing.title,
                "city": listing.city,
                "price": str(listing.price),
                "tenant": listing.get_tenant_type_display(),
                "url": reverse("listing", kwargs={"listing_id": listing.id}),
                "lat": lat + spread,
                "lng": lon - spread,
            }
        )
    return points


def _city_choice_labels():
    return [city for city, _label in BANGLADESH_CITY_CHOICES]


def _safe_redirect_url(request):
    cand = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if not cand:
        return None
    if cand.startswith("/") and not cand.startswith("//"):
        return cand
    if url_has_allowed_host_and_scheme(
        url=cand,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return cand
    return None


@ensure_csrf_cookie
def index(request):
    if request.GET.get("clear_prefs") == "1":
        request.session.pop("preferred_city", None)
        request.session.pop("preferred_tenant", None)
        request.session.modified = True
        return redirect("listings")

    _sync_tenant_from_query(request)

    pref_city = (request.session.get("preferred_city") or "").strip()
    tenant = _active_tenant(request)

    listings_qs = Listing.objects.filter(is_published=True)
    listings_qs = filter_by_tenant(listings_qs, tenant)
    listings_qs = order_city_first(listings_qs, pref_city)

    # Smart Match Score - rule-based ranking (listings/matching.py)
    smart_matches = None
    if "city" in request.GET and "budget" in request.GET:
        city = request.GET.get("city")
        budget = float(request.GET.get("budget", 0))
        priority = request.GET.get("priority")  # 'space' or 'luxury' or 'price'

        candidates = Listing.objects.filter(city__iexact=city, is_published=True)
        candidates = filter_by_tenant(candidates, tenant)

        ranked = matching.rank_listings(
            candidates, city=city, budget=budget, tenant=tenant, priority=priority
        )
        smart_matches = [row["listing"] for row in ranked[:3]]

    paginator = Paginator(listings_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    cities = _city_choice_labels()

    get_params = request.GET.copy()
    get_params.pop("page", None)
    # Keep tenant in pager links when filter comes from session only (?page=2).
    if not get_params.get("tenant") and tenant:
        get_params["tenant"] = tenant
    pagination_query = get_params.urlencode()

    if pref_city:
        spotlight_ordered = listings_qs.filter(is_verified=True).order_by(
            "_near_you", "-views_count"
        )
    else:
        spotlight_ordered = listings_qs.filter(is_verified=True).order_by(
            "-views_count"
        )
    verified = list(spotlight_ordered[:8])
    if len(verified) < 8:
        have = {p.pk for p in verified}
        for row in listings_qs:
            if row.pk in have:
                continue
            verified.append(row)
            have.add(row.pk)
            if len(verified) >= 8:
                break
    spotlight_listings = verified[:8]

    show_spotlight = smart_matches is None and (request.GET.get("page") or "1") == "1"

    context = {
        "page_obj": page_obj,
        "listings": page_obj,
        "smart_matches": smart_matches,
        "cities": cities,
        "total_listings": listings_qs.count(),
        "city_count": Listing.objects.filter(is_published=True)
        .values("city")
        .distinct()
        .count(),
        "pagination_query": pagination_query,
        "spotlight_listings": spotlight_listings if show_spotlight else [],
    }
    return render(request, "listings/listings.html", context)


def listing_legacy_redirect(request, listing_id):
    """Permanent redirect from legacy /104 URLs to /property/104/."""
    url = reverse("listing", kwargs={"listing_id": listing_id})
    return HttpResponsePermanentRedirect(url)


def listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)

    # Analytics Tracking
    listing.views_count += 1
    listing.save()

    reviews = listing.reviews.all().order_by("-created_at")

    # NEW: AI Neighborhood & Living Cost
    ai_insight = get_neighborhood_insight(listing.address, listing.city)
    living_cost = get_living_cost_estimate(listing.city, listing.price)

    # Rent Fairness Estimator (prototype comparator, listings/fairness.py)
    fairness_result = fairness.rent_fairness(listing)
    price_status = fairness_result["label"]
    price_color = fairness_result["color"]

    from . import trust_score as trust_score_module

    trust_label_text, trust_color = trust_score_module.trust_label(listing.trust_score)

    is_favorited = False
    if request.user.is_authenticated:
        if Favorite.objects.filter(user=request.user, listing=listing).exists():
            is_favorited = True

    now = timezone.now()
    listing_offers = list(
        ListingOffer.objects.filter(
            listing=listing,
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
        ).order_by("-bonus_points_on_inquiry", "-discount_percent")[:5]
    )
    primary_offer = listing_offers[0] if listing_offers else None
    offer_discounted_price = None
    if primary_offer and primary_offer.discount_percent:
        offer_discounted_price = (
            listing.price * Decimal(100 - primary_offer.discount_percent) / 100
        ).quantize(Decimal("0.01"))

    context = {
        "listing": listing,
        "reviews": reviews,
        "is_favorited": is_favorited,
        "price_status": price_status,
        "price_color": price_color,
        "fairness": fairness_result,
        "trust_label_text": trust_label_text,
        "trust_color": trust_color,
        "ai_insight": ai_insight,
        "living_cost": living_cost,
        "listing_offers": listing_offers,
        "primary_offer": primary_offer,
        "offer_discounted_price": offer_discounted_price,
    }
    if not request.user.is_authenticated:
        context["login_form"] = AuthenticationForm(prefix="inquiry_login")
        context["register_form"] = RegisterForm(prefix="inquiry_register")
    return render(request, "listings/listing.html", context)


@login_required
def compare_properties(request):
    compare_ids = request.session.get("compare_list", [])
    listings = Listing.objects.filter(id__in=compare_ids)
    return render(request, "listings/compare.html", {"listings": listings})


def add_to_compare(request, listing_id):
    compare_list = request.session.get("compare_list", [])
    if len(compare_list) >= 3:
        messages.warning(request, "You can only compare 3 properties at a time.")
    elif listing_id not in compare_list:
        compare_list.append(listing_id)
        request.session["compare_list"] = compare_list
        messages.success(request, "Added to comparison list.")

    return redirect("compare_properties")


def clear_compare(request):
    request.session["compare_list"] = []
    return redirect("listings")


@login_required
def add_review(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        # Check if user already reviewed
        if Review.objects.filter(user=request.user, listing=listing).exists():
            messages.error(request, "You have already reviewed this property.")
        else:
            Review.objects.create(
                listing=listing, user=request.user, rating=rating, comment=comment
            )
            grant_review_points(request.user, listing)
            messages.success(
                request, "Review added successfully. You earned reward points!"
            )

    return redirect("listing", listing_id=listing_id)


@login_required
def toggle_favorite(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    favorite = Favorite.objects.filter(user=request.user, listing=listing)

    if favorite.exists():
        favorite.delete()
        messages.success(request, "Property removed from favorites.")
    else:
        Favorite.objects.create(user=request.user, listing=listing)
        grant_favorite_points(request.user, listing)
        messages.success(
            request, "Property added to favorites. You earned reward points!"
        )

    return redirect(request.META.get("HTTP_REFERER", "listings"))


@ratelimit(key="ip", rate="10/m", method="POST")
@require_POST
def submit_complaint(request, listing_id):
    if getattr(request, "limited", False):
        messages.error(request, "Too many reports from this network. Please wait.")
        return redirect("listing", listing_id=listing_id)

    listing = get_object_or_404(Listing, pk=listing_id)
    category = request.POST.get("category", Complaint.Category.OTHER)
    message = (request.POST.get("message") or "").strip()

    if not message:
        messages.error(request, "Please describe the issue before submitting.")
        return redirect("listing", listing_id=listing_id)

    complaint = Complaint(
        listing=listing,
        category=category
        if category in Complaint.Category.values
        else Complaint.Category.OTHER,
        message=message,
    )
    if request.user.is_authenticated:
        complaint.reporter = request.user
    else:
        complaint.reporter_name = (request.POST.get("reporter_name") or "").strip()
        complaint.reporter_email = (request.POST.get("reporter_email") or "").strip()
    complaint.save()

    messages.success(request, "Thanks - your report has been sent to the admin team.")
    return redirect("listing", listing_id=listing_id)


@login_required
def favorites_view(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("listing")
        .order_by("-created_at")
    )
    return render(request, "auth/favorites.html", {"favorites": favorites})


@ratelimit(key="ip", rate="20/m", method="POST")
def contact(request):
    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(
            request, "Too many inquiries from this network. Please wait and try again."
        )
        lid = request.POST.get("listing_id")
        if lid:
            return redirect("listing", listing_id=lid)
        return redirect("listings")

    if request.method != "POST":
        return redirect("listings")

    if not request.user.is_authenticated:
        messages.warning(request, "Please register or log in to send an inquiry.")
        lid = request.POST.get("listing_id")
        if lid:
            return redirect("listing", listing_id=lid)
        return redirect("listings")

    listing_id = request.POST["listing_id"]
    listing_obj = get_object_or_404(Listing, pk=listing_id)
    name = request.POST["name"]
    email = request.POST["email"]
    phone = request.POST["phone"]
    message_body = request.POST["message"]
    user_id = request.user.id

    has_contacted = Inquiry.objects.filter(listing_id=listing_id, user_id=user_id)
    if has_contacted.exists():
        messages.error(request, "You have already made an inquiry for this listing")
        return redirect("listing", listing_id=listing_id)

    inquiry = Inquiry(
        listing_id=listing_id,
        name=name,
        email=email,
        phone=phone,
        message=message_body,
        user_id=user_id,
    )
    inquiry.save()

    extra = 0
    promo = ListingOffer.objects.filter(
        listing=listing_obj,
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_until__gte=timezone.now(),
    ).first()
    if promo:
        extra = promo.bonus_points_on_inquiry
    grant_inquiry_points(request.user, listing_obj, extra_offer_points=extra)
    total_pts = POINTS_INQUIRY + extra
    messages.success(
        request,
        f"Your inquiry has been submitted successfully. You earned {total_pts} reward points!",
    )
    return redirect("listing", listing_id=listing_id)


def search(request):
    if request.GET.get("reset") == "1":
        request.session.pop("preferred_tenant", None)
        request.session.modified = True
        return redirect("search")

    _sync_tenant_from_query(request)

    pref_city = (request.session.get("preferred_city") or "").strip()
    tenant = _active_tenant(request)

    queryset_list = Listing.objects.filter(is_published=True)
    queryset_list = filter_by_tenant(queryset_list, tenant)
    queryset_list = order_city_first(queryset_list, pref_city)

    if "keywords" in request.GET:
        keywords = request.GET["keywords"].strip().lower()
        if keywords:
            # Semantic shortcuts
            if "luxury" in keywords:
                queryset_list = queryset_list.filter(is_furnished=True)
            if "spacious" in keywords:
                queryset_list = queryset_list.filter(square_feet__gte=1500)
            queryset_list = queryset_list.filter(
                Q(title__icontains=keywords)
                | Q(description__icontains=keywords)
                | Q(address__icontains=keywords)
                | Q(city__icontains=keywords)
            )

    if "city" in request.GET:
        city = request.GET["city"]
        if city:
            queryset_list = queryset_list.filter(city__iexact=city)

    if "bedrooms" in request.GET:
        bedrooms = request.GET["bedrooms"]
        if bedrooms:
            queryset_list = queryset_list.filter(bedrooms__lte=bedrooms)

    if "price" in request.GET:
        price = request.GET["price"]
        if price:
            queryset_list = queryset_list.filter(price__lte=price)

    sort = request.GET.get("sort")
    if sort == "match":
        ranked = matching.rank_listings(
            queryset_list,
            city=request.GET.get("city") or None,
            budget=request.GET.get("price") or None,
            tenant=tenant,
        )
        pageable = [row["listing"] for row in ranked]
    else:
        pageable = queryset_list

    # Pagination (same page size as home browse for consistency)
    paginator = Paginator(pageable, 12)
    page = request.GET.get("page")
    paged_listings = paginator.get_page(page)

    chip_params = request.GET.copy()
    chip_params.pop("page", None)
    chip_params.pop("tenant", None)
    chip_query = chip_params.urlencode()

    context = {
        "listings": paged_listings,
        "values": request.GET,
        "chip_query": chip_query,
        "result_count": queryset_list.count(),
        "map_points": _map_points_for_listings(queryset_list[:80]),
        "city_choices": _city_choice_labels(),
        "active_filters": bool(
            (request.GET.get("keywords") or "").strip()
            or (request.GET.get("city") or "").strip()
            or (request.GET.get("price") or "").strip()
            or (request.GET.get("bedrooms") or "").strip()
            or tenant,
        ),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "listings/_listing_items.html", context)

    return render(request, "listings/search.html", context)


@ratelimit(key="ip", rate="30/m", method="POST")
@require_POST
def api_set_visitor_preferences(request):
    """Store preferred city / tenant type; or skip location modal."""
    if getattr(request, "limited", False):
        return JsonResponse({"ok": False, "error": "Too many requests."}, status=429)

    try:
        data = json.loads(request.body.decode())
    except json.JSONDecodeError:
        return JsonResponse({"ok": False}, status=400)

    if data.get("skip"):
        request.session["rf_location_prompt_done"] = True
        request.session.modified = True
        return JsonResponse({"ok": True})

    city = (data.get("city") or "").strip()[:100]
    tenant = (data.get("tenant") or "").strip().lower()
    if tenant not in ("", *TENANT_FILTER_VALUES):
        tenant = ""

    if city:
        request.session["preferred_city"] = city
    else:
        request.session.pop("preferred_city", None)

    if tenant:
        request.session["preferred_tenant"] = tenant
    else:
        request.session.pop("preferred_tenant", None)

    request.session["rf_location_prompt_done"] = True
    request.session.modified = True
    return JsonResponse(
        {
            "ok": True,
            "preferred_city": city or None,
            "preferred_tenant": tenant or None,
        }
    )


@ratelimit(key="ip", rate="20/m", method="POST")
@require_POST
def api_resolve_location(request):
    """Reverse-geocode lat/lon to city name (uses OpenStreetMap Nominatim)."""
    if getattr(request, "limited", False):
        return JsonResponse({"error": "Too many requests."}, status=429)

    try:
        data = json.loads(request.body.decode())
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid coordinates."}, status=400)

    known = list(
        Listing.objects.filter(is_published=True)
        .values_list("city", flat=True)
        .distinct()
    )
    city = reverse_geocode_city(lat, lon, known)
    return JsonResponse({"city": city})


@ratelimit(key="ip", rate="40/m", method="POST")
@require_POST
def ai_assistant_chat(request):
    """Public JSON API: AI rental assistant with rate limits (guest session / user daily)."""
    if getattr(request, "limited", False):
        return JsonResponse(
            {"error": "Too many requests from this address. Please wait a moment."},
            status=429,
        )

    cap_guest = getattr(dj_settings, "AI_ASSISTANT_GUEST_MESSAGE_CAP", 5)
    cap_user = getattr(dj_settings, "AI_ASSISTANT_USER_DAILY_CAP", 100)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is empty."}, status=400)
    if len(message) > 4000:
        return JsonResponse({"error": "Message is too long."}, status=400)

    today = timezone.localdate()

    if request.user.is_authenticated:
        row = AiAssistantDailyUsage.objects.filter(user=request.user, day=today).first()
        if row and row.count >= cap_user:
            return JsonResponse(
                {
                    "error": f"Daily limit reached ({cap_user} messages). Try again tomorrow.",
                    "remaining": 0,
                    "limit": cap_user,
                    "logged_in": True,
                },
                status=429,
            )
    else:
        if not request.session.session_key:
            request.session.create()
        used = request.session.get("ai_assistant_guest_count", 0)
        if used >= cap_guest:
            return JsonResponse(
                {
                    "error": f"Guest limit reached ({cap_guest} messages). Log in for up to {cap_user} messages per day.",
                    "remaining": 0,
                    "limit": cap_guest,
                    "logged_in": False,
                },
                status=429,
            )

    try:
        reply, suggested = assistant_chat_reply(message)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    if request.user.is_authenticated:
        row, _ = AiAssistantDailyUsage.objects.get_or_create(
            user=request.user, day=today, defaults={"count": 0}
        )
        row.count += 1
        row.save(update_fields=["count"])
        remaining = max(0, cap_user - row.count)
    else:
        request.session["ai_assistant_guest_count"] = (
            request.session.get("ai_assistant_guest_count", 0) + 1
        )
        request.session.modified = True
        remaining = max(0, cap_guest - request.session["ai_assistant_guest_count"])

    return JsonResponse(
        {
            "reply": reply,
            "suggested": suggested,
            "remaining": remaining,
            "limit": cap_user if request.user.is_authenticated else cap_guest,
            "logged_in": request.user.is_authenticated,
        }
    )


@login_required
@ratelimit(key="user", rate="40/h", method="POST")
def generate_ai_description_api(request):
    if getattr(request, "limited", False) and request.method == "POST":
        return JsonResponse(
            {"error": "Too many AI description requests. Try again later."},
            status=429,
        )
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ai_description = generate_property_description(data)
            return JsonResponse({"description": ai_description})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=405)


# Management Views
@login_required
def dashboard(request):
    user_listings = (
        Listing.objects.filter(owner=request.user)
        .annotate(inquiry_count=Count("inquiries"))
        .order_by("-list_date")
    )
    inquiries = (
        Inquiry.objects.filter(listing__owner=request.user)
        .select_related("listing")
        .order_by("-contact_date")
    )
    total_inquiries = inquiries.count()
    total_listings = user_listings.count()
    if total_listings:
        engagement_rate = round(
            100 * user_listings.filter(inquiry_count__gt=0).count() / total_listings, 0
        )
    else:
        engagement_rate = 0

    # Pagination for properties table
    paginator = Paginator(user_listings, 5)  # 5 rows per scroll
    page = request.GET.get("page")
    paged_listings = paginator.get_page(page)

    from .models import Booking, Hotel, PropertyListing

    context = {
        "listings": paged_listings,
        "inquiries": inquiries,
        "total_inquiries": total_inquiries,
        "total_listings": total_listings,
        "engagement_rate": int(engagement_rate),
        "property_listings": PropertyListing.objects.filter(
            owner=request.user
        ).order_by("-list_date"),
        "hotels": Hotel.objects.filter(manager=request.user)
        .prefetch_related("rooms")
        .order_by("-list_date"),
        "bookings": Booking.objects.filter(user=request.user)
        .select_related("room", "room__hotel")
        .order_by("-created_at"),
        "profile": roles.get_profile(request.user),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "auth/_dashboard_items.html", context)

    return render(request, "auth/dashboard.html", context)


@role_required(Profile.Role.FLAT_OWNER)
def add_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES)
        files = request.FILES.getlist("images")
        try:
            for f in files:
                validate_listing_image_file(f)
        except FormValidationError as exc:
            messages.error(request, exc.messages[0])
            return render(request, "auth/add_listing.html", {"form": form})

        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.is_published = True
            main_image_file = form.cleaned_data.get("main_image")
            if main_image_file:
                listing.main_image_hash = duplicates.hash_uploaded_file(main_image_file)
            listing.save()
            grant_new_listing_points(request.user, listing)

            # Handle multiple images
            for f in files:
                ListingImage.objects.create(
                    listing=listing,
                    image=f,
                    image_hash=duplicates.hash_uploaded_file(f),
                )

            try:
                duplicates.apply_flags(listing, duplicates.scan_listing(listing))
            except Exception:
                pass

            messages.success(
                request,
                "Property listed successfully with gallery. You earned reward points!",
            )
            return redirect("dashboard")
    else:
        form = ListingForm()
    return render(request, "auth/add_listing.html", {"form": form})


@login_required
def edit_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, owner=request.user)
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES, instance=listing)
        files = request.FILES.getlist("images")
        try:
            for f in files:
                validate_listing_image_file(f)
        except FormValidationError as exc:
            messages.error(request, exc.messages[0])
            return render(
                request, "auth/edit_listing.html", {"form": form, "listing": listing}
            )

        if form.is_valid():
            listing = form.save(commit=False)
            main_image_file = form.cleaned_data.get("main_image")
            if main_image_file:
                listing.main_image_hash = duplicates.hash_uploaded_file(main_image_file)
            listing.save()

            # Handle additional images
            for f in files:
                ListingImage.objects.create(
                    listing=listing,
                    image=f,
                    image_hash=duplicates.hash_uploaded_file(f),
                )

            try:
                duplicates.apply_flags(listing, duplicates.scan_listing(listing))
            except Exception:
                pass

            messages.success(request, "Property updated successfully")
            return redirect("dashboard")
    else:
        form = ListingForm(instance=listing)
    return render(request, "auth/edit_listing.html", {"form": form, "listing": listing})


@login_required
def delete_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id, owner=request.user)
    if request.method == "POST":
        listing.delete()
        messages.success(request, "Property removed successfully")
        return redirect("dashboard")
    return render(request, "auth/delete_confirm.html", {"listing": listing})


@login_required
def messages_view(request):
    inquiries = Inquiry.objects.filter(listing__owner=request.user).order_by(
        "-contact_date"
    )
    return render(request, "auth/messages.html", {"inquiries": inquiries})


@login_required
def profile_view(request):
    return render(
        request,
        "auth/profile.html",
        {"wallet_summary": wallet_summary(request.user)},
    )


@login_required
def rewards_view(request):
    summary = wallet_summary(request.user)
    ledger = PointsLedger.objects.filter(user=request.user).select_related("listing")[
        :100
    ]
    progress = tier_progress(summary["lifetime_points"])
    earn_rows = [
        {"action": "Create your account", "points": POINTS_SIGNUP},
        {"action": "Send a property inquiry", "points": POINTS_INQUIRY},
        {"action": "Post a review", "points": POINTS_REVIEW},
        {"action": "Save a favorite", "points": POINTS_FAVORITE},
        {"action": "Publish a listing (landlords)", "points": POINTS_NEW_LISTING},
    ]
    return render(
        request,
        "auth/rewards.html",
        {
            "summary": summary,
            "ledger": ledger,
            "tier_progress": progress,
            "earn_rows": earn_rows,
        },
    )


# Auth Views
@ratelimit(key="ip", rate="10/m", method="POST")
def register_view(request):
    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(request, "Too many registration attempts. Please wait a minute.")
        form = RegisterForm()
        return render(request, "auth/register.html", {"form": form}, status=429)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get("role") or Profile.Role.USER
            roles.create_profile_for_user(user, role)
            grant_signup_bonus(user)
            login(request, user)
            nxt = _safe_redirect_url(request)
            if nxt:
                return redirect(nxt)
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "auth/register.html", {"form": form})


@ratelimit(key="ip", rate="15/m", method="POST")
def login_view(request):
    if getattr(request, "limited", False) and request.method == "POST":
        messages.error(request, "Too many login attempts. Please wait a minute.")
        form = AuthenticationForm()
        return render(request, "auth/login.html", {"form": form}, status=429)

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            nxt = _safe_redirect_url(request)
            if nxt:
                return redirect(nxt)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("listings")
