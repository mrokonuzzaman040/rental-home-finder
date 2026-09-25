from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, Hotel, Room


class RoomInline(admin.TabularInline):
    model = Room
    extra = 0


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "name",
        "manager_display",
        "city",
        "is_published",
        "is_verified",
        "list_date",
    )
    list_display_links = ("thumb", "name")
    list_editable = ("is_published", "is_verified")
    list_filter = ("city", "is_published", "is_verified")
    search_fields = ("name", "description", "address", "city", "contact_phone")
    autocomplete_fields = ("manager",)
    readonly_fields = ("list_date",)
    date_hierarchy = "list_date"
    ordering = ("-list_date",)
    inlines = [RoomInline]

    @admin.display(description="Image")
    def thumb(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" alt="" width="52" height="40" style="object-fit:cover;border-radius:2px"/>',
                obj.main_image.url,
            )
        return "-"

    @admin.display(description="Manager")
    def manager_display(self, obj):
        return obj.manager.username if obj.manager_id else "-"


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "room",
        "user",
        "check_in",
        "check_out",
        "guests",
        "status_badge",
        "created_at",
    )
    list_filter = ("status", "check_in")
    search_fields = ("room__room_type", "room__hotel__name", "user__username")
    raw_id_fields = ("room", "user")
    date_hierarchy = "check_in"
    ordering = ("-created_at",)
    actions = ["mark_confirmed", "mark_cancelled"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            Booking.Status.PENDING: "#c77700",
            Booking.Status.CONFIRMED: "#1a7f4a",
            Booking.Status.CANCELLED: "#6c757d",
        }
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    @admin.action(description="Mark selected bookings as confirmed")
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status=Booking.Status.CONFIRMED)
        self.message_user(request, f"Confirmed {updated} bookings.")

    @admin.action(description="Mark selected bookings as cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status=Booking.Status.CANCELLED)
        self.message_user(request, f"Cancelled {updated} bookings.")
