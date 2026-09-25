from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from .choices import BANGLADESH_CITY_CHOICES


class RewardReason(models.TextChoices):
    SIGNUP = "signup", "Welcome bonus"
    INQUIRY_SENT = "inquiry_sent", "Property inquiry"
    REVIEW_POSTED = "review_posted", "Review posted"
    FAVORITE_ADDED = "favorite_added", "Saved favorite"
    LISTING_PUBLISHED = "listing_published", "Published listing"
    OFFER_INQUIRY_BONUS = "offer_inquiry_bonus", "Promo: inquiry bonus"
    OTHER = "other", "Other"


class Profile(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        FLAT_OWNER = "flat_owner", "Flat Owner"
        PROPERTY_OWNER = "property_owner", "Property Owner"
        HOTEL_MANAGER = "hotel_manager", "Hotel Manager"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.USER, db_index=True
    )
    phone = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Listing(models.Model):
    class TenantType(models.TextChoices):
        BACHELOR = "bachelor", "Bachelor"
        FAMILY = "family", "Family"
        GIRL = "girl", "Girl"
        ANY = "any", "Any"

    STATUS_CHOICES = [
        ("available", "Available"),
        ("rented", "Rented"),
        ("pending", "Pending"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, choices=BANGLADESH_CITY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    square_feet = models.IntegerField()
    garage = models.IntegerField(default=0)
    is_furnished = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    has_heating = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )
    tenant_type = models.CharField(
        max_length=20,
        choices=TenantType.choices,
        default=TenantType.ANY,
        db_index=True,
        help_text="Who this rental best suits: bachelor, family, girl, or any.",
    )
    main_image = models.ImageField(upload_to="listings/", blank=True, null=True)
    is_published = models.BooleanField(default=True)
    list_date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    views_count = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Owner/landlord phone shown to renters; also used for verification and duplicate detection.",
    )
    tenant_fit_note = models.TextField(
        blank=True,
        default="",
        help_text='Free text, e.g. "Suitable for female students, small family, and job holders. Not allowed: bachelor male group."',
    )

    # Verified Listing Trust Score inputs (weights in listings/trust_score.py)
    phone_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(
        default=False, help_text="Address checked by admin."
    )
    photos_verified = models.BooleanField(
        default=False, help_text="Real property photos uploaded."
    )
    rent_confirmed = models.BooleanField(default=False)
    availability_confirmed = models.BooleanField(default=False)
    document_checked = models.BooleanField(
        default=False,
        help_text="Owner/landlord document checked privately by admin. Not shown publicly.",
    )
    trust_score = models.PositiveSmallIntegerField(default=0, editable=False)
    main_image_hash = models.CharField(
        max_length=64, blank=True, default="", db_index=True
    )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        from . import trust_score as trust_score_module

        self.trust_score = trust_score_module.compute_trust_score(self)
        super().save(*args, **kwargs)


class ListingImage(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="listings/gallery/")
    image_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    def __str__(self):
        return f"Image for {self.listing.title}"


class Inquiry(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="inquiries"
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    contact_date = models.DateTimeField(auto_now_add=True)
    user_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Inquiry for {self.listing.title} by {self.name}"


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "listing")


class Review(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} star by {self.user.username} for {self.listing.title}"


class RewardWallet(models.Model):
    """One wallet per user: spendable balance + lifetime earned for tiers."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="reward_wallet"
    )
    balance = models.PositiveIntegerField(default=0)
    lifetime_points = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reward wallet"
        verbose_name_plural = "Reward wallets"

    def __str__(self):
        return f"{self.user.username} - {self.balance} pts"

    @staticmethod
    def tier_from_lifetime(lifetime: int) -> str:
        if lifetime >= 2500:
            return "gold"
        if lifetime >= 600:
            return "silver"
        return "bronze"

    @staticmethod
    def tier_label_from_lifetime(lifetime: int) -> str:
        return {
            "gold": "Gold",
            "silver": "Silver",
            "bronze": "Bronze",
        }[RewardWallet.tier_from_lifetime(lifetime)]

    @property
    def tier_code(self) -> str:
        return self.tier_from_lifetime(self.lifetime_points)

    @property
    def tier_display_name(self) -> str:
        return self.tier_label_from_lifetime(self.lifetime_points)


class PointsLedger(models.Model):
    """Audit log of point grants (and future redemptions)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="points_ledger"
    )
    points = models.IntegerField(
        help_text="Positive for earned; negative when redeeming (future)."
    )
    reason = models.CharField(max_length=32, choices=RewardReason.choices)
    balance_after = models.PositiveIntegerField(default=0)
    listing = models.ForeignKey(
        "Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="points_events",
    )
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Points entry"
        verbose_name_plural = "Points ledger"

    def __str__(self):
        return f"{self.user.username} {self.points:+d} ({self.get_reason_display()})"


class AiAssistantDailyUsage(models.Model):
    """Logged-in users: chat messages counted per calendar day (timezone-aware)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ai_assistant_daily"
    )
    day = models.DateField(db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [["user", "day"]]
        verbose_name = "AI assistant daily usage"

    def __str__(self):
        return f"{self.user.username} {self.day}: {self.count}"


class ListingOffer(models.Model):
    """Time-bound promotions on a listing (managed in admin)."""

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="offers"
    )
    title = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
        help_text="Optional rent discount shown to renters (e.g. 10 for 10%).",
    )
    bonus_points_on_inquiry = models.PositiveIntegerField(
        default=0,
        help_text="Extra reward points for logged-in users who send an inquiry during this promo.",
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valid_from"]

    def __str__(self):
        return f"{self.title} - {self.listing.title}"

    def is_current(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        return self.valid_from <= now <= self.valid_until


class Complaint(models.Model):
    """User-submitted report against a listing, reviewed by admin."""

    class Category(models.TextChoices):
        FAKE = "fake", "Fake / misleading listing"
        FRAUD = "fraud", "Fraud / scam"
        WRONG_INFO = "wrong_info", "Incorrect information"
        OFFENSIVE = "offensive", "Offensive content"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="complaints"
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints_filed",
    )
    reporter_name = models.CharField(max_length=200, blank=True)
    reporter_email = models.EmailField(blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    message = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Complaint on {self.listing.title} ({self.get_status_display()})"


class ListingFlag(models.Model):
    """Rule-based duplicate/fake-listing detection result, reviewed by admin."""

    class Rule(models.TextChoices):
        PHONE_REUSE = "phone_reuse", "Phone reused across many listings"
        ADDRESS_PRICE_MISMATCH = (
            "address_price_mismatch",
            "Same address, different rents",
        )
        LOW_RENT_AREA = "low_rent_area", "Rent far below area average"
        TEXT_SIMILARITY = "text_similarity", "Very similar title/description"
        IMAGE_REUSE = "image_reuse", "Repeated image across listings"

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="flags")
    related_listing = models.ForeignKey(
        Listing, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    rule = models.CharField(max_length=32, choices=Rule.choices, db_index=True)
    detail = models.CharField(max_length=255, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_rule_display()} - {self.listing.title}"


class PropertyListing(models.Model):
    """Property for sale (buy & sell module) - separate from the rental Listing model."""

    class PropertyKind(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        LAND = "land", "Land"
        HOUSE = "house", "House"
        COMMERCIAL = "commercial", "Commercial space"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNDER_NEGOTIATION = "under_negotiation", "Under negotiation"
        SOLD = "sold", "Sold"

    title = models.CharField(max_length=200)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, choices=BANGLADESH_CITY_CHOICES)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    property_kind = models.CharField(
        max_length=20, choices=PropertyKind.choices, default=PropertyKind.APARTMENT
    )
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    square_feet = models.IntegerField()
    main_image = models.ImageField(upload_to="property_sales/", blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True
    )
    is_published = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="property_listings"
    )
    list_date = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-list_date"]

    def __str__(self):
        return self.title


class PropertyImage(models.Model):
    property_listing = models.ForeignKey(
        PropertyListing, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="property_sales/gallery/")

    def __str__(self):
        return f"Image for {self.property_listing.title}"


class PropertyInterest(models.Model):
    """Buy interest / inquiry from a normal user on a for-sale property."""

    property_listing = models.ForeignKey(
        PropertyListing, on_delete=models.CASCADE, related_name="interests"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_interests",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    offered_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Interest in {self.property_listing.title} by {self.name}"


class Hotel(models.Model):
    """Hotel listed by a Hotel Manager (rent/booking module)."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100, choices=BANGLADESH_CITY_CHOICES)
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    main_image = models.ImageField(upload_to="hotels/", blank=True, null=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hotels")
    is_published = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    list_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-list_date"]

    def __str__(self):
        return self.name


class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="rooms")
    room_type = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveSmallIntegerField(default=2)
    total_rooms = models.PositiveSmallIntegerField(default=1)
    is_published = models.BooleanField(default=True)
    main_image = models.ImageField(upload_to="hotels/rooms/", blank=True, null=True)

    def __str__(self):
        return f"{self.room_type} - {self.hotel.name}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.room} booked by {self.user.username} ({self.check_in} to {self.check_out})"
