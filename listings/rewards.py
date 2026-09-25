"""Points, tiers, and reward grants for user actions."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from .models import PointsLedger, RewardReason, RewardWallet

# Points awarded per action (tune freely)
POINTS_SIGNUP = 100
POINTS_INQUIRY = 25
POINTS_REVIEW = 40
POINTS_FAVORITE = 15
POINTS_NEW_LISTING = 50


def get_wallet(user: User) -> RewardWallet:
    wallet, _ = RewardWallet.objects.get_or_create(user=user)
    return wallet


def wallet_summary(user: User) -> dict:
    wallet = RewardWallet.objects.filter(user=user).first()
    if not wallet:
        return {
            "balance": 0,
            "lifetime_points": 0,
            "tier": RewardWallet.tier_from_lifetime(0),
            "tier_label": RewardWallet.tier_label_from_lifetime(0),
        }
    return {
        "balance": wallet.balance,
        "lifetime_points": wallet.lifetime_points,
        "tier": wallet.tier_code,
        "tier_label": wallet.tier_display_name,
    }


def award_points(
    user: User,
    points: int,
    reason: str,
    *,
    listing=None,
    note: str = "",
    skip_if_duplicate_reason: bool = False,
) -> PointsLedger | None:
    """
    Grant points and append ledger row. Returns None if skipped or points <= 0.
    If skip_if_duplicate_reason is True, does nothing if user already has a ledger row with this reason.
    """
    if points <= 0:
        return None

    if skip_if_duplicate_reason:
        qs = PointsLedger.objects.filter(user=user, reason=reason)
        if qs.exists():
            return None

    with transaction.atomic():
        wallet = RewardWallet.objects.select_for_update().get_or_create(user=user)[0]
        RewardWallet.objects.filter(pk=wallet.pk).update(
            balance=F("balance") + points,
            lifetime_points=F("lifetime_points") + points,
        )
        wallet.refresh_from_db(fields=["balance", "lifetime_points"])
        entry = PointsLedger.objects.create(
            user=user,
            points=points,
            reason=reason,
            listing=listing,
            note=note[:500] if note else "",
            balance_after=wallet.balance,
        )
    return entry


def grant_signup_bonus(user: User) -> PointsLedger | None:
    return award_points(
        user,
        POINTS_SIGNUP,
        RewardReason.SIGNUP,
        note="Welcome to Rental Finder",
        skip_if_duplicate_reason=True,
    )


def grant_inquiry_points(user: User, listing, extra_offer_points: int = 0) -> None:
    award_points(
        user,
        POINTS_INQUIRY,
        RewardReason.INQUIRY_SENT,
        listing=listing,
        note="Inquiry sent",
    )
    if extra_offer_points > 0:
        award_points(
            user,
            extra_offer_points,
            RewardReason.OFFER_INQUIRY_BONUS,
            listing=listing,
            note="Listing promotion bonus",
        )


def grant_review_points(user: User, listing) -> None:
    award_points(
        user,
        POINTS_REVIEW,
        RewardReason.REVIEW_POSTED,
        listing=listing,
    )


def grant_favorite_points(user: User, listing) -> None:
    award_points(
        user,
        POINTS_FAVORITE,
        RewardReason.FAVORITE_ADDED,
        listing=listing,
    )


def grant_new_listing_points(user: User, listing) -> None:
    award_points(
        user,
        POINTS_NEW_LISTING,
        RewardReason.LISTING_PUBLISHED,
        listing=listing,
        note="New property listing",
    )


def tier_progress(lifetime_points: int) -> dict:
    """Points needed for next tier and a simple progress indicator."""
    lp = lifetime_points
    if lp >= 2500:
        return {
            "at_max": True,
            "next_label": None,
            "points_to_next": 0,
            "progress_pct": 100,
            "hint": "You are at the top tier - thank you for being active!",
        }
    if lp >= 600:
        goal = 2500
        span = goal - 600
        delta = lp - 600
        return {
            "at_max": False,
            "next_label": "Gold",
            "points_to_next": goal - lp,
            "progress_pct": min(99, max(1, int(100 * delta / span))),
            "hint": f"{goal - lp} lifetime points to Gold.",
        }
    goal = 600
    span = goal
    return {
        "at_max": False,
        "next_label": "Silver",
        "points_to_next": goal - lp,
        "progress_pct": min(99, max(1, int(100 * lp / span))),
        "hint": f"{goal - lp} lifetime points to Silver.",
    }
