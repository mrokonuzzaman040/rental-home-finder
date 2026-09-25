from datetime import timedelta

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    AiAssistantDailyUsage,
    Complaint,
    Favorite,
    Inquiry,
    Listing,
    ListingFlag,
    ListingImage,
    ListingOffer,
    PointsLedger,
    Profile,
    Review,
    RewardWallet,
)
from . import duplicates, trust_score


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
    verbose_name_plural = "Gallery images"


class ListingOfferInline(admin.StackedInline):
    model = ListingOffer
    extra = 0
    fk_name = "listing"


class ComplaintInline(admin.TabularInline):
    model = Complaint
    extra = 0
    fields = ("category", "status", "message", "reporter", "created_at")
    readonly_fields = ("category", "message", "reporter", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ListingFlagInline(admin.TabularInline):
    model = ListingFlag
    fk_name = "listing"
    extra = 0
    fields = ("rule", "detail", "score", "resolved", "created_at")
    readonly_fields = ("rule", "detail", "score", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "title",
        "owner_display",
        "city",
        "tenant_badge",
        "price_display",
        "bedrooms",
        "status_badge",
        "trust_score_badge",
        "is_published",
        "is_verified",
        "views_count",
        "list_date",
    )
    list_display_links = ("thumb", "title")
    list_editable = ("is_published", "is_verified")
    list_filter = (
        "city",
        "tenant_type",
        "status",
        "is_published",
        "is_verified",
        "is_furnished",
        "has_ac",
        "phone_verified",
        "address_verified",
        "photos_verified",
        "rent_confirmed",
        "availability_confirmed",
        "document_checked",
        "list_date",
    )
    search_fields = ("title", "description", "address", "city", "contact_phone")
    autocomplete_fields = ("owner",)
    readonly_fields = ("list_date", "views_count", "listing_preview", "trust_score")
    date_hierarchy = "list_date"
    ordering = ("-list_date",)
    list_per_page = 25
    save_on_top = True
    inlines = [ListingImageInline, ListingOfferInline, ComplaintInline, ListingFlagInline]
    actions = ["recompute_trust_scores", "rescan_duplicates_action"]

    fieldsets = (
        (
            "Listing",
            {"fields": ("title", "description", "owner", "contact_phone")},
        ),
        (
            "Location",
            {"fields": ("address", "city", "tenant_type", "tenant_fit_note")},
        ),
        (
            "Rent & availability",
            {"fields": ("price", "status", "is_published", "is_verified")},
        ),
        (
            "Property details",
            {"fields": ("bedrooms", "bathrooms", "square_feet", "garage")},
        ),
        (
            "Trust & Verification",
            {
                "fields": (
                    "phone_verified",
                    "address_verified",
                    "photos_verified",
                    "rent_confirmed",
                    "availability_confirmed",
                    "document_checked",
                    "trust_score",
                )
            },
        ),
        (
            "Features",
            {
                "fields": ("is_furnished", "has_ac", "has_heating"),
                "classes": ("collapse",),
            },
        ),
        (
            "Media",
            {"fields": ("main_image", "listing_preview")},
        ),
        (
            "Metrics",
            {"fields": ("views_count", "list_date"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        trust_score.recompute_and_save(obj)

    @admin.action(description="Recompute trust score")
    def recompute_trust_scores(self, request, queryset):
        for listing in queryset:
            trust_score.recompute_and_save(listing)
        self.message_user(request, f"Recomputed trust score for {queryset.count()} listings.")

    @admin.action(description="Re-run duplicate/fake-listing scan")
    def rescan_duplicates_action(self, request, queryset):
        summary = duplicates.rescan_all(queryset)
        self.message_user(
            request,
            f"Scanned {summary['scanned']} listings, created {summary['flags_created']} flags.",
        )

    @admin.display(description="Trust", ordering="trust_score")
    def trust_score_badge(self, obj):
        if obj.trust_score >= 85:
            color = "#1a7f4a"
        elif obj.trust_score >= 50:
            color = "#c77700"
        else:
            color = "#6c757d"
        return format_html(
            '<span style="color:{};font-weight:600">{}/100</span>', color, obj.trust_score
        )

    @admin.display(description="Image")
    def thumb(self, obj):
        if obj.main_image:
            url = obj.main_image.url
            return format_html(
                '<img src="{}" alt="" width="52" height="40" style="object-fit:cover;border-radius:2px"/>',
                url,
            )
        return "-"

    @admin.display(description="Owner")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner_id else "-"

    @admin.display(description="Rent", ordering="price")
    def price_display(self, obj):
        return f"৳{obj.price:,.0f}"

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        css = {
            "available": "rf-badge--avail",
            "rented": "rf-badge--rented",
            "pending": "rf-badge--pending",
        }.get(obj.status, "")
        return format_html(
            '<span class="rf-badge {}">{}</span>',
            css,
            obj.get_status_display(),
        )

    @admin.display(description="Tenant", ordering="tenant_type")
    def tenant_badge(self, obj):
        css = {
            Listing.TenantType.BACHELOR: "rf-badge--tenant-b",
            Listing.TenantType.FAMILY: "rf-badge--tenant-f",
            Listing.TenantType.ANY: "rf-badge--tenant-a",
        }.get(obj.tenant_type, "")
        return format_html(
            '<span class="rf-badge {}">{}</span>',
            css,
            obj.get_tenant_type_display(),
        )

    @admin.display(description="Main photo")
    def listing_preview(self, obj):
        if not obj.pk or not obj.main_image:
            return "-"
        return format_html(
            '<img src="{}" style="max-width:320px;height:auto;border:1px solid #dee2e6"/>',
            obj.main_image.url,
        )


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ("id", "thumb", "listing", "image")
    list_display_links = ("id", "thumb")
    list_filter = ("listing__city",)
    search_fields = ("listing__title",)
    autocomplete_fields = ("listing",)
    ordering = ("listing", "id")

    @admin.display(description="Preview")
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" alt="" width="72" height="54" style="object-fit:cover;border-radius:2px"/>',
                obj.image.url,
            )
        return "-"


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "name",
        "email",
        "phone",
        "message_preview",
        "account_hint",
        "contact_date",
    )
    list_filter = ("contact_date", "listing__city")
    search_fields = ("name", "email", "phone", "message", "listing__title")
    readonly_fields = ("contact_date", "account_hint")
    ordering = ("-contact_date",)
    date_hierarchy = "contact_date"
    raw_id_fields = ("listing",)

    fieldsets = (
        (
            "Lead",
            {"fields": ("listing", "name", "email", "phone", "message")},
        ),
        (
            "Meta",
            {
                "fields": ("user_id", "account_hint", "contact_date"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Message")
    def message_preview(self, obj):
        if not obj.message:
            return "-"
        text = obj.message.strip().replace("\n", " ")
        if len(text) > 72:
            text = text[:69] + "…"
        return text

    @admin.display(description="Account")
    def account_hint(self, obj):
        if not obj.user_id:
            return "Guest"
        try:
            u = User.objects.get(pk=obj.user_id)
            return u.username
        except User.DoesNotExist:
            return format_html(
                '<span class="text-warning">User #{} (missing)</span>', obj.user_id
            )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "listing", "listing_city", "created_at")
    list_filter = ("created_at", "listing__city")
    search_fields = ("user__username", "listing__title")
    autocomplete_fields = ("user", "listing")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    @admin.display(description="City", ordering="listing__city")
    def listing_city(self, obj):
        return obj.listing.city


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "user", "stars", "created_at")
    list_filter = ("rating", "created_at", "listing__city")
    search_fields = ("comment", "listing__title", "user__username")
    autocomplete_fields = ("listing", "user")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    @admin.display(description="Rating")
    def stars(self, obj):
        return f"{obj.rating} / 5"


@admin.register(RewardWallet)
class RewardWalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "lifetime_points", "tier_column", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("balance", "lifetime_points", "updated_at")
    raw_id_fields = ("user",)

    @admin.display(description="Tier")
    def tier_column(self, obj):
        return obj.tier_display_name


@admin.register(PointsLedger)
class PointsLedgerAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "points_colored",
        "reason",
        "balance_after",
        "listing",
    )
    list_filter = ("reason", "created_at")
    search_fields = ("user__username", "note", "listing__title")
    readonly_fields = (
        "user",
        "points",
        "reason",
        "balance_after",
        "listing",
        "note",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Points", ordering="points")
    def points_colored(self, obj):
        cls = "rf-points-pos" if obj.points >= 0 else "rf-points-neg"
        sign = "+" if obj.points > 0 else ""
        return format_html('<span class="{}">{}{}</span>', cls, sign, obj.points)

    def has_add_permission(self, request):
        return False


@admin.register(AiAssistantDailyUsage)
class AiAssistantDailyUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "day", "count")
    list_filter = ("day",)
    search_fields = ("user__username",)
    ordering = ("-day", "-count")
    date_hierarchy = "day"


@admin.register(ListingOffer)
class ListingOfferAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "listing",
        "discount_display",
        "bonus_points_on_inquiry",
        "valid_from",
        "valid_until",
        "is_active",
        "is_current_badge",
    )
    list_filter = ("is_active",)
    search_fields = ("title", "description", "listing__title")
    raw_id_fields = ("listing",)
    date_hierarchy = "valid_from"
    readonly_fields = ("created_at",)

    @admin.display(description="Discount")
    def discount_display(self, obj):
        if obj.discount_percent is not None:
            return f"{obj.discount_percent}% off"
        return "-"

    @admin.display(description="Active now", boolean=True)
    def is_current_badge(self, obj):
        return obj.is_current()


admin.site.unregister(Group)

admin.site.unregister(User)


class RewardWalletInline(admin.StackedInline):
    model = RewardWallet
    extra = 0
    max_num = 1
    can_delete = False
    readonly_fields = ("balance", "lifetime_points", "updated_at")


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    max_num = 1
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Slightly clearer columns for support staff."""

    inlines = (ProfileInline, RewardWalletInline)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role_display",
        "reward_balance_display",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    ordering = ("-date_joined",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("reward_wallet", "profile")
        )

    @admin.display(description="Role")
    def role_display(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "-"

    @admin.display(description="Rewards")
    def reward_balance_display(self, obj):
        w = getattr(obj, "reward_wallet", None)
        if not w:
            return "-"
        return format_html(
            '<span title="Lifetime earned">{}</span> <span class="text-muted">/ {} pts</span>',
            w.tier_display_name,
            w.balance,
        )


def _filled_from_map(start_day, end_day, by_day):
    """Build chart labels + values; missing days default to 0."""
    labels = []
    values = []
    d = start_day
    while d <= end_day:
        labels.append(d.strftime("%b %d"))
        raw = by_day.get(d, 0)
        values.append(int(raw))
        d += timedelta(days=1)
    return labels, values


def _admin_dashboard_payload(request):
    """Analytics + shortcuts for the admin control center (staff only)."""
    empty_chart = {"labels": [], "data": []}
    empty_pie = {"labels": [], "data": [], "colors": []}
    empty = {
        "stats": {},
        "inquiry_chart": empty_chart,
        "listing_status_chart": empty_pie,
        "ai_usage_chart": empty_chart,
        "recent_inquiries": [],
        "top_listings": [],
        "recent_users": [],
        "quick_actions": [],
    }
    try:
        now = timezone.now()
        today = timezone.localdate()
        week_ago = now - timedelta(days=7)
        inquiry_start = today - timedelta(days=29)
        ai_start = today - timedelta(days=13)

        ai_today = (
            AiAssistantDailyUsage.objects.filter(day=today).aggregate(s=Sum("count"))[
                "s"
            ]
            or 0
        )

        iq_rows = (
            Inquiry.objects.filter(contact_date__date__gte=inquiry_start)
            .annotate(d=TruncDate("contact_date"))
            .values("d")
            .annotate(c=Count("id"))
        )
        iq_map = {}
        for row in iq_rows:
            key = row["d"]
            if hasattr(key, "date"):
                key = key.date()
            iq_map[key] = row["c"]
        iq_labels, iq_data = _filled_from_map(inquiry_start, today, iq_map)

        status_lookup = dict(Listing.STATUS_CHOICES)
        status_rows = list(
            Listing.objects.values("status").annotate(c=Count("id")).order_by("status")
        )
        pie_labels = [status_lookup.get(r["status"], r["status"]) for r in status_rows]
        pie_data = [r["c"] for r in status_rows]
        palette = ["#1a7f4a", "#6c757d", "#ffc107", "#0dcaf0", "#6610f2", "#fd7e14"]

        ai_rows = (
            AiAssistantDailyUsage.objects.filter(day__gte=ai_start)
            .values("day")
            .annotate(s=Sum("count"))
            .order_by("day")
        )
        ai_map = {row["day"]: row["s"] for row in ai_rows}
        ai_labels, ai_data = _filled_from_map(ai_start, today, ai_map)

        recent_inquiries = list(
            Inquiry.objects.select_related("listing").order_by("-contact_date")[:10]
        )
        top_listings = list(Listing.objects.order_by("-views_count")[:8])
        recent_users = list(User.objects.order_by("-date_joined")[:6])

        stats = {
            "listings_total": Listing.objects.count(),
            "listings_published": Listing.objects.filter(is_published=True).count(),
            "listings_unverified": Listing.objects.filter(is_verified=False).count(),
            "inquiries_week": Inquiry.objects.filter(
                contact_date__gte=week_ago
            ).count(),
            "inquiries_total": Inquiry.objects.count(),
            "favorites_total": Favorite.objects.count(),
            "wallets_count": RewardWallet.objects.count(),
            "ai_messages_today": int(ai_today),
            "reviews_total": Review.objects.count(),
            "users_total": User.objects.count(),
            "users_active": User.objects.filter(is_active=True).count(),
            "staff_count": User.objects.filter(is_staff=True).count(),
            "new_users_week": User.objects.filter(date_joined__gte=week_ago).count(),
            "offers_active": ListingOffer.objects.filter(is_active=True).count(),
        }

        quick_actions = []
        try:
            quick_actions = [
                {
                    "title": "Unverified listings",
                    "subtitle": "Verify or reject",
                    "url": reverse("admin:listings_listing_changelist")
                    + "?is_verified__exact=0",
                    "icon": "fas fa-user-check",
                    "variant": "outline-success",
                },
                {
                    "title": "Pending rentals",
                    "subtitle": "Status = pending",
                    "url": reverse("admin:listings_listing_changelist")
                    + "?status__exact=pending",
                    "icon": "fas fa-hourglass-half",
                    "variant": "outline-warning",
                },
                {
                    "title": "All inquiries",
                    "subtitle": "Leads & messages",
                    "url": reverse("admin:listings_inquiry_changelist"),
                    "icon": "fas fa-envelope-open-text",
                    "variant": "outline-primary",
                },
                {
                    "title": "Reward wallets",
                    "subtitle": "Points & tiers",
                    "url": reverse("admin:listings_rewardwallet_changelist"),
                    "icon": "fas fa-wallet",
                    "variant": "outline-secondary",
                },
                {
                    "title": "AI usage",
                    "subtitle": "Daily chat volume",
                    "url": reverse("admin:listings_aiassistantdailyusage_changelist"),
                    "icon": "fas fa-robot",
                    "variant": "outline-info",
                },
                {
                    "title": "Staff users",
                    "subtitle": "Admins & support",
                    "url": reverse("admin:auth_user_changelist") + "?is_staff__exact=1",
                    "icon": "fas fa-user-shield",
                    "variant": "outline-dark",
                },
            ]
        except Exception:
            quick_actions = []

        return {
            "stats": stats,
            "inquiry_chart": {"labels": iq_labels, "data": iq_data},
            "listing_status_chart": {
                "labels": pie_labels,
                "data": pie_data,
                "colors": palette[: len(pie_data)],
            },
            "ai_usage_chart": {"labels": ai_labels, "data": ai_data},
            "recent_inquiries": recent_inquiries,
            "top_listings": top_listings,
            "recent_users": recent_users,
            "quick_actions": quick_actions,
        }
    except Exception:
        return empty


_original_admin_index = AdminSite.index


def _admin_index_with_stats(self, request, extra_context=None):
    extra_context = dict(extra_context or {})
    extra_context["dashboard"] = _admin_dashboard_payload(request)
    extra_context["dashboard_stats"] = extra_context["dashboard"].get("stats") or {}
    return _original_admin_index(self, request, extra_context)


AdminSite.index = _admin_index_with_stats
admin.site.index_template = "admin/rental_dashboard.html"

from . import admin_moderation, admin_property, admin_hotel  # noqa: E402,F401
