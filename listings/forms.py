from pathlib import Path

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Booking, Hotel, Listing, Profile, PropertyListing, Room

_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_listing_image_file(upload):
    """Validate optional gallery uploads (same rules as main_image)."""
    if not upload:
        return
    if getattr(upload, "size", 0) > _MAX_IMAGE_BYTES:
        raise ValidationError("Each gallery image must be 5 MB or smaller.")
    ext = Path(getattr(upload, "name", "") or "").suffix.lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Gallery images must be JPG, PNG, or WEBP.")


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            "title",
            "city",
            "address",
            "tenant_type",
            "price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "garage",
            "is_furnished",
            "has_ac",
            "has_heating",
            "status",
            "main_image",
            "description",
            "contact_phone",
            "tenant_fit_note",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control rounded-0",
                    "placeholder": "e.g. Modern Apartment in Banani",
                }
            ),
            "city": forms.Select(attrs={"class": "form-select rounded-0"}),
            "tenant_type": forms.Select(attrs={"class": "form-select rounded-0"}),
            "address": forms.TextInput(
                attrs={
                    "class": "form-control rounded-0",
                    "placeholder": "Road 11, Block H",
                }
            ),
            "price": forms.NumberInput(attrs={"class": "form-control rounded-0"}),
            "bedrooms": forms.NumberInput(attrs={"class": "form-control rounded-0"}),
            "bathrooms": forms.NumberInput(attrs={"class": "form-control rounded-0"}),
            "square_feet": forms.NumberInput(attrs={"class": "form-control rounded-0"}),
            "garage": forms.NumberInput(attrs={"class": "form-control rounded-0"}),
            "status": forms.Select(attrs={"class": "form-select rounded-0"}),
            "description": forms.Textarea(
                attrs={"class": "form-control rounded-0", "rows": 5}
            ),
            "main_image": forms.FileInput(attrs={"class": "form-control rounded-0"}),
            "contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control rounded-0",
                    "placeholder": "+880 1XXX-XXXXXX",
                }
            ),
            "tenant_fit_note": forms.Textarea(
                attrs={
                    "class": "form-control rounded-0",
                    "rows": 2,
                    "placeholder": "e.g. Suitable for female students, small family, and job holders. Not allowed: bachelor male group.",
                }
            ),
        }

    def clean_main_image(self):
        f = self.cleaned_data.get("main_image")
        if not f:
            return f
        if getattr(f, "size", 0) > _MAX_IMAGE_BYTES:
            raise ValidationError("Image must be 5 MB or smaller.")
        ext = Path(getattr(f, "name", "") or "").suffix.lower()
        if ext not in _ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError("Use JPG, PNG, or WEBP.")
        return f


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control rounded-0", "placeholder": "you@example.com"}
        ),
    )
    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        initial=Profile.Role.USER,
        required=False,
        label="I am a...",
        widget=forms.Select(attrs={"class": "form-select rounded-0"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""
        self.fields["username"].widget.attrs.update(
            {"class": "form-control rounded-0", "placeholder": "Choose a username"}
        )
        for field_name in ("password1", "password2"):
            self.fields[field_name].help_text = ""
            self.fields[field_name].widget.attrs.update(
                {"class": "form-control rounded-0"}
            )

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already exists with this email address.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


_TEXT_INPUT = forms.TextInput(attrs={"class": "form-control rounded-0"})
_NUMBER_INPUT = forms.NumberInput(attrs={"class": "form-control rounded-0"})
_SELECT_INPUT = forms.Select(attrs={"class": "form-select rounded-0"})
_TEXTAREA_INPUT = forms.Textarea(attrs={"class": "form-control rounded-0", "rows": 5})
_FILE_INPUT = forms.FileInput(attrs={"class": "form-control rounded-0"})


class PropertyListingForm(forms.ModelForm):
    class Meta:
        model = PropertyListing
        fields = [
            "title",
            "city",
            "address",
            "property_kind",
            "sale_price",
            "bedrooms",
            "bathrooms",
            "square_feet",
            "contact_phone",
            "status",
            "main_image",
            "description",
        ]
        widgets = {
            "title": _TEXT_INPUT,
            "city": _SELECT_INPUT,
            "address": _TEXT_INPUT,
            "property_kind": _SELECT_INPUT,
            "sale_price": _NUMBER_INPUT,
            "bedrooms": _NUMBER_INPUT,
            "bathrooms": _NUMBER_INPUT,
            "square_feet": _NUMBER_INPUT,
            "contact_phone": _TEXT_INPUT,
            "status": _SELECT_INPUT,
            "main_image": _FILE_INPUT,
            "description": _TEXTAREA_INPUT,
        }

    def clean_main_image(self):
        f = self.cleaned_data.get("main_image")
        if not f:
            return f
        if getattr(f, "size", 0) > _MAX_IMAGE_BYTES:
            raise ValidationError("Image must be 5 MB or smaller.")
        ext = Path(getattr(f, "name", "") or "").suffix.lower()
        if ext not in _ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError("Use JPG, PNG, or WEBP.")
        return f


class HotelForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = [
            "name",
            "city",
            "address",
            "contact_phone",
            "main_image",
            "description",
        ]
        widgets = {
            "name": _TEXT_INPUT,
            "city": _SELECT_INPUT,
            "address": _TEXT_INPUT,
            "contact_phone": _TEXT_INPUT,
            "main_image": _FILE_INPUT,
            "description": _TEXTAREA_INPUT,
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            "room_type",
            "price_per_night",
            "capacity",
            "total_rooms",
            "main_image",
            "is_published",
        ]
        widgets = {
            "room_type": _TEXT_INPUT,
            "price_per_night": _NUMBER_INPUT,
            "capacity": _NUMBER_INPUT,
            "total_rooms": _NUMBER_INPUT,
            "main_image": _FILE_INPUT,
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["check_in", "check_out", "guests"]
        widgets = {
            "check_in": forms.DateInput(
                attrs={"class": "form-control rounded-0", "type": "date"}
            ),
            "check_out": forms.DateInput(
                attrs={"class": "form-control rounded-0", "type": "date"}
            ),
            "guests": _NUMBER_INPUT,
        }

    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get("check_in")
        check_out = cleaned.get("check_out")
        if check_in and check_out and check_in >= check_out:
            raise ValidationError("Check-out date must be after check-in date.")
        return cleaned
