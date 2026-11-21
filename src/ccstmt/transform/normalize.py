"""Merchant name normalization."""

import re


def normalize_merchant(description: str) -> str:
    """Normalize merchant description.

    - Remove payment gateway prefixes (PAYU*, RAZ*, etc.)
    - Remove long digit runs
    - Remove city/country suffixes
    - Collapse whitespace
    """
    if not description:
        return ""

    text = description.upper().strip()

    # Remove common gateway prefixes
    text = re.sub(r"^(PAYU|RAZ|PYU|CCAV)\*", "", text)

    # Remove long digit runs (reference numbers, etc.)
    text = re.sub(r"\d{10,}", "", text)

    # Remove common suffixes (city, country, state codes)
    text = re.sub(r"\s+(INDIA|IND|USA|US|UK|CA|AU)$", "", text)
    text = re.sub(r"\s+[A-Z]{2}$", "", text)  # State/country codes

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
