"""Reverse geocode lat/lon to a city name (Bangladesh-focused)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import urlencode

USER_AGENT = "RentalHomeFinder/1.0 (contact: https://example.com/contact)"


def reverse_geocode_city(lat: float, lon: float, known_cities: list[str]) -> str | None:
    """
    Call Nominatim reverse API and match result to known_cities when possible.
    Returns None on failure or no usable city.
    """
    params = urlencode(
        {"lat": lat, "lon": lon, "format": "json", "addressdetails": "1"}
    )
    url = f"https://nominatim.openstreetmap.org/reverse?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    addr = payload.get("address") or {}
    raw_candidates = [
        addr.get("city"),
        addr.get("town"),
        addr.get("village"),
        addr.get("state_district"),
        addr.get("county"),
        addr.get("suburb"),
    ]

    known_lower = {k.lower(): k for k in known_cities if k}

    for cand in raw_candidates:
        if not cand:
            continue
        low = cand.strip().lower()
        if low in known_lower:
            return known_lower[low]
    # Common alias when DB uses "Chittagong"
    for cand in raw_candidates:
        if not cand:
            continue
        low = cand.strip().lower()
        if low == "chattogram" and "chittagong" in known_lower:
            return known_lower["chittagong"]

    # Fallback: first non-empty raw string if it looks like a placename in BD context
    for cand in raw_candidates:
        if cand and len(cand.strip()) <= 100:
            return cand.strip()

    return None
