"""Country mapping helpers. Unknown locations remain unknown; never guess from a vague string."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_COUNTRY_ALIASES = {
    "Vietnam": {"vietnam", "viet nam", "socialist republic of vietnam"},
    "United States": {"united states", "united states of america", "usa", "u s a", "us"},
    "United Kingdom": {"united kingdom", "uk", "great britain", "britain", "england", "scotland", "wales"},
    "Canada": {"canada"},
    "Australia": {"australia"},
    "India": {"india"},
    "China": {"china", "people s republic of china"},
    "Japan": {"japan"},
    "South Korea": {"south korea", "republic of korea", "korea republic"},
    "Singapore": {"singapore"},
    "Germany": {"germany"},
    "France": {"france"},
    "Netherlands": {"netherlands", "the netherlands", "holland"},
    "Brazil": {"brazil"},
    "Russia": {"russia", "russian federation"},
    "Ukraine": {"ukraine"},
    "Spain": {"spain"},
    "Italy": {"italy"},
    "Sweden": {"sweden"},
    "Norway": {"norway"},
    "Finland": {"finland"},
    "Denmark": {"denmark"},
    "Switzerland": {"switzerland"},
    "Ireland": {"ireland"},
    "New Zealand": {"new zealand"},
    "Indonesia": {"indonesia"},
    "Thailand": {"thailand"},
    "Malaysia": {"malaysia"},
    "Philippines": {"philippines"},
    "Pakistan": {"pakistan"},
    "Bangladesh": {"bangladesh"},
    "Taiwan": {"taiwan"},
    "Hong Kong": {"hong kong"},
    "Mexico": {"mexico"},
    "Argentina": {"argentina"},
    "Colombia": {"colombia"},
    "South Africa": {"south africa"},
    "Turkey": {"turkey", "turkiye"},
    "Poland": {"poland"},
    "Portugal": {"portugal"},
    "Belgium": {"belgium"},
    "Austria": {"austria"},
    "Israel": {"israel"},
    "United Arab Emirates": {"united arab emirates", "uae"},
    "Saudi Arabia": {"saudi arabia"},
}

_VIETNAM_CITY_ALIASES = {
    "hanoi", "ha noi", "ho chi minh city", "ho chi minh", "saigon",
    "da nang", "danang", "hai phong", "can tho", "quy nhon",
    "nha trang", "vietnam", "viet nam",
}


def resolve_country(location: Optional[str]) -> Optional[str]:
    """Return a cautious country label from a public, self-reported profile location."""
    if not location or not location.strip():
        return None

    normalized = normalize_text(location)
    if not normalized:
        return None

    # Vietnam cities are recognized only from explicit city names in the location.
    if any(re.search(rf"\b{re.escape(city)}\b", normalized) for city in _VIETNAM_CITY_ALIASES):
        return "Vietnam"

    # Match complete comma-separated segments first (e.g. "Paris, France").
    segments = [normalize_text(part) for part in re.split(r"[,;|]", location)]
    for segment in segments:
        for country, aliases in _COUNTRY_ALIASES.items():
            if segment in aliases:
                return country

    # For unstructured locations, only accept explicit multi-word country names.
    # Avoid guesses such as mapping "CA" or "Georgia" without context.
    for country, aliases in _COUNTRY_ALIASES.items():
        for alias in aliases:
            if len(alias.split()) > 1 and re.search(rf"\b{re.escape(alias)}\b", normalized):
                return country

    return None
