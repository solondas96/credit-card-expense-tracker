"""Redaction for sensitive data before LLM processing."""

import re


def redact_card_numbers(text: str) -> tuple[str, dict]:
    """Mask card numbers and extract last 4 digits.

    Returns (redacted_text, card_numbers_found):
    - Masks 12-19 digit sequences (with spaces/dashes) to XXXX…<last4>
    - Returns dict mapping original sequence to last4
    """
    # Pattern: 12-19 digits with optional spaces/dashes
    # Examples: 1234-5678-9012-3456, 1234 5678 9012 3456, 123456789012345
    pattern = r"\b(?:\d{4}[\s\-]?){3}\d{4}|\d{12,19}\b"

    card_map = {}
    redacted = text

    for match in re.finditer(pattern, text):
        original = match.group(0)
        # Extract just the digits
        digits_only = re.sub(r"\D", "", original)

        if len(digits_only) >= 4:
            last4 = digits_only[-4:]
            redacted_str = f"XXXX…{last4}"
            redacted = redacted.replace(original, redacted_str)
            card_map[original] = last4

    return redacted, card_map


def extract_card_last4(text: str) -> str:
    """Extract last 4 digits of a card number from text.

    Looks for the first 12-19 digit sequence and returns last 4.
    """
    pattern = r"(?:\d{4}[\s\-]?){3}\d{4}|\d{12,19}"
    match = re.search(pattern, text)

    if match:
        digits_only = re.sub(r"\D", "", match.group(0))
        if len(digits_only) >= 4:
            return digits_only[-4:]

    return ""
