"""User role helpers (Normal User / Flat Owner / Property Owner / Hotel Manager)."""

from .models import Profile


def get_profile(user) -> Profile:
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def create_profile_for_user(user, role: str) -> Profile:
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"role": role})
    return profile


def role_of(user) -> str:
    if not user.is_authenticated:
        return Profile.Role.USER
    return get_profile(user).role


def can_add_rental(user) -> bool:
    return user.is_staff or role_of(user) == Profile.Role.FLAT_OWNER


def can_add_property(user) -> bool:
    return user.is_staff or role_of(user) == Profile.Role.PROPERTY_OWNER


def can_add_hotel(user) -> bool:
    return user.is_staff or role_of(user) == Profile.Role.HOTEL_MANAGER
