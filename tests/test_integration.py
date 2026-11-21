"""Integration tests for the full pipeline."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from ccstmt.extract.schema import StatementExtract, TransactionExtract
from ccstmt.transform.categorize import Categorizer
from ccstmt.transform.normalize import normalize_merchant


def test_normalize_merchant():
    """Test merchant normalization."""
    test_cases = [
        ("PAYU*AMAZON.IN BENGALURU", "AMAZON.IN BENGALURU"),
        ("RAZ*FLIPKART BANGALORE IND", "FLIPKART BANGALORE"),
        ("SWIGGY  NEW  DELHI", "SWIGGY NEW DELHI"),
    ]

    for input_val, expected in test_cases:
        result = normalize_merchant(input_val)
        assert expected in result, f"Expected {expected} in {result}"


def test_categorizer_basic():
    """Test categorization with basic rules."""
    # Create a minimal categorizer (uses config/categories.yaml)
    from tempfile import NamedTemporaryFile
    import yaml

    # Create temp categories file
    categories_config = {
        "categories": [
            {"pattern": "AMAZON", "category": "shopping_online"},
            {"pattern": "ZOMATO|SWIGGY", "category": "food_delivery"},
            {"pattern": "HDFC|AXIS", "category": "bank_transfer"},
        ],
        "default_category": "uncategorized",
    }

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(categories_config, f)
        temp_path = Path(f.name)

    try:
        categorizer = Categorizer(temp_path)

        # Test categorization
        category, source = categorizer.categorize("AMAZON purchase")
        assert category == "shopping_online", f"Got {category}"
        assert source == "rule"

        category, source = categorizer.categorize("ZOMATO order")
        assert category == "food_delivery"

        category, source = categorizer.categorize("unknown merchant")
        assert category == "uncategorized"
        assert source == "default"

    finally:
        temp_path.unlink()


def test_statement_extract_with_categories():
    """Test that transaction extract can store categories."""
    txn = TransactionExtract(
        txn_date=date(2024, 11, 15),
        description="AMAZON BENGALURU",
        amount=Decimal("1000.00"),
        direction="debit",
    )

    # Add category fields
    txn.category = "shopping_online"
    txn.category_source = "rule"

    assert txn.category == "shopping_online"
    assert txn.category_source == "rule"


def test_full_pipeline_mock():
    """Test full pipeline with mock data (no external APIs)."""
    # Create test statement
    stmt = StatementExtract(
        issuer="hdfc",
        card_last4="1234",
        currency="INR",
        statement_date=date(2024, 11, 22),
        total_amount_due=Decimal("5000.00"),
        transactions=[
            TransactionExtract(
                txn_date=date(2024, 11, 15),
                description="AMAZON.IN",
                amount=Decimal("2000.00"),
                direction="debit",
            ),
            TransactionExtract(
                txn_date=date(2024, 11, 20),
                description="ZOMATO",
                amount=Decimal("500.00"),
                direction="debit",
            ),
        ],
    )

    # Apply normalization and categorization
    from tempfile import NamedTemporaryFile
    import yaml

    categories_config = {
        "categories": [
            {"pattern": "AMAZON", "category": "shopping_online"},
            {"pattern": "ZOMATO", "category": "food_delivery"},
        ],
        "default_category": "uncategorized",
    }

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(categories_config, f)
        temp_path = Path(f.name)

    try:
        categorizer = Categorizer(temp_path)

        for txn in stmt.transactions:
            txn.description = normalize_merchant(txn.description)
            category, source = categorizer.categorize(txn.description)
            txn.category = category
            txn.category_source = source

        # Verify results
        assert stmt.transactions[0].category == "shopping_online"
        assert stmt.transactions[1].category == "food_delivery"
        assert all(t.category_source == "rule" for t in stmt.transactions)

    finally:
        temp_path.unlink()
