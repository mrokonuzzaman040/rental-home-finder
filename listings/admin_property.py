from django.contrib import admin
from django.utils.html import format_html

from .models import PropertyImage, PropertyInterest, PropertyListing


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    verbose_name_plural = "Gallery images"


@admin.register(PropertyListing)
class PropertyListingAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "title",
        "owner_display",
        "city",
        "property_kind",
        "price_display",
        "status",
        "is_published",
        "is_verified",
        "views_count",
        "list_date",
    )
    list_display_links = ("thumb", "title")
    list_editable = ("is_published", "is_verified")
    list_filter = ("city", "property_kind", "status", "is_published", "is_verified")
    search_fields = ("title", "description", "address", "city", "contact_phone")
    autocomplete_fields = ("owner",)
    readonly_fields = ("list_date", "views_count")
    date_hierarchy = "list_date"
    ordering = ("-list_date",)
    inlines = [PropertyImageInline]

    @admin.display(description="Image")
    def thumb(self, obj):
        if obj.main_image:
            return format_html(
                '<img src="{}" alt="" width="52" height="40" style="object-fit:cover;border-radius:2px"/>',
                obj.main_image.url,
            )
        return "-"

    @admin.display(description="Owner")
    def owner_display(self, obj):
        return obj.owner.username if obj.owner_id else "-"

    @admin.display(description="Price", ordering="sale_price")
    def price_display(self, obj):
        return f"৳{obj.sale_price:,.0f}"


@admin.register(PropertyInterest)
class PropertyInterestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property_listing",
        "name",
        "email",
        "phone",
        "offered_price",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "email", "phone", "property_listing__title")
    raw_id_fields = ("property_listing", "user")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
