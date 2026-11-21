"""PDF processing tests."""

from ccstmt.pdf.redact import redact_card_numbers, extract_card_last4


def test_redact_card_numbers_with_dashes():
    """Test card redaction with dashes."""
    text = "Card number is 1234-5678-9012-3456 on the statement"
    redacted, card_map = redact_card_numbers(text)

    assert "XXXX…3456" in redacted
    assert "1234-5678-9012-3456" in card_map
    assert card_map["1234-5678-9012-3456"] == "3456"


def test_redact_card_numbers_with_spaces():
    """Test card redaction with spaces."""
    text = "Card 1234 5678 9012 3456 is used"
    redacted, card_map = redact_card_numbers(text)

    assert "XXXX…3456" in redacted
    assert len(card_map) > 0


def test_extract_card_last4():
    """Test extracting last 4 digits."""
    text = "Your card 1234-5678-9012-3456 expires"
    last4 = extract_card_last4(text)

    assert last4 == "3456"


def test_extract_card_last4_no_card():
    """Test extraction when no card found."""
    text = "No card number here"
    last4 = extract_card_last4(text)

    assert last4 == ""
