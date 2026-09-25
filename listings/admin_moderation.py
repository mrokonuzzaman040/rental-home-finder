from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Complaint, ListingFlag
from . import trust_score


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "category_badge",
        "status_badge",
        "reporter_display",
        "created_at",
        "resolved_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("listing__title", "message", "reporter_name", "reporter_email")
    raw_id_fields = ("listing", "reporter")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Report",
            {"fields": ("listing", "category", "message", "created_at")},
        ),
        (
            "Reporter",
            {"fields": ("reporter", "reporter_name", "reporter_email")},
        ),
        (
            "Review",
            {"fields": ("status", "admin_note", "resolved_at")},
        ),
    )

    @admin.display(description="Reporter")
    def reporter_display(self, obj):
        if obj.reporter_id:
            return obj.reporter.username
        return obj.reporter_name or obj.reporter_email or "Anonymous"

    @admin.display(description="Category")
    def category_badge(self, obj):
        return obj.get_category_display()

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            Complaint.Status.OPEN: "#c0392b",
            Complaint.Status.IN_REVIEW: "#c77700",
            Complaint.Status.RESOLVED: "#1a7f4a",
            Complaint.Status.REJECTED: "#6c757d",
        }
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and obj.status in (
            Complaint.Status.RESOLVED,
            Complaint.Status.REJECTED,
        ):
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)
        trust_score.recompute_and_save(obj.listing)


@admin.register(ListingFlag)
class ListingFlagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "rule_display",
        "related_listing",
        "detail",
        "score",
        "resolved",
        "created_at",
    )
    list_editable = ("resolved",)
    list_filter = ("rule", "resolved", "created_at")
    search_fields = ("listing__title", "detail")
    raw_id_fields = ("listing", "related_listing")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = ["mark_resolved"]

    @admin.display(description="Rule")
    def rule_display(self, obj):
        return obj.get_rule_display()

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark selected flags as resolved")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(resolved=True)
        self.message_user(request, f"Marked {updated} flags as resolved.")
