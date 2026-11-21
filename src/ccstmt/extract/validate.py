"""Statement validation and reconciliation checks."""

from decimal import Decimal

from ccstmt.extract.schema import StatementExtract


class ValidationResult:
    """Result of validation checks."""

    def __init__(self):
        """Initialize validation result."""
        self.passed = True
        self.warnings = []
        self.notes = {}

    def add_warning(self, field: str, message: str):
        """Add a validation warning."""
        self.warnings.append(f"{field}: {message}")
        self.notes[field] = message

    def __bool__(self):
        """True if all checks passed."""
        return self.passed


def validate_statement(statement: StatementExtract) -> ValidationResult:
    """Run reconciliation checks on extracted statement.

    Returns ValidationResult. Failing checks set needs_review flag but don't reject.
    """
    result = ValidationResult()

    # Check 1: Balance reconciliation (tolerance ₹1.00)
    if all(
        [
            statement.previous_balance is not None,
            statement.payments_credits is not None,
            statement.purchases_debits is not None,
            statement.fees_charges is not None,
        ]
    ):
        expected_balance = (
            statement.previous_balance
            - statement.payments_credits
            + statement.purchases_debits
            + statement.fees_charges
        )
        tolerance = Decimal("1.00")

        if abs(expected_balance - statement.total_amount_due) > tolerance:
            delta = abs(expected_balance - statement.total_amount_due)
            result.add_warning(
                "balance_reconciliation",
                f"Mismatch: expected {expected_balance}, got "
                f"{statement.total_amount_due} (delta ₹{delta})",
            )

    # Check 2: Transaction debit sum
    debit_sum = sum(
        (t.amount for t in statement.transactions if t.direction == "debit"),
        Decimal("0"),
    )
    if statement.purchases_debits is not None:
        tolerance = Decimal("1.00")
        if abs(debit_sum - statement.purchases_debits) > tolerance:
            result.add_warning(
                "debit_reconciliation",
                f"Transaction sum {debit_sum} != purchases_debits "
                f"{statement.purchases_debits}",
            )

    # Check 3: Date range
    if statement.period_start and statement.period_end:
        txn_dates = [t.txn_date for t in statement.transactions]
        min_date = min(txn_dates) if txn_dates else statement.period_start
        max_date = max(txn_dates) if txn_dates else statement.period_end

        grace_days = 3
        from datetime import timedelta

        if min_date < (
            statement.period_start - timedelta(days=grace_days)
        ) or max_date > (statement.period_end + timedelta(days=grace_days)):
            result.add_warning(
                "date_range",
                f"Transactions outside period {statement.period_start} to "
                f"{statement.period_end}",
            )

    # Check 4: Card last4 format
    if not (statement.card_last4 and len(statement.card_last4) == 4):
        result.add_warning(
            "card_format", f"card_last4 '{statement.card_last4}' is not 4 digits"
        )

    # Check 5: No zero amounts
    for i, txn in enumerate(statement.transactions):
        if txn.amount == 0:
            result.add_warning(
                "zero_amount", f"Transaction {i} has zero amount"
            )

    # Check 6: No exact duplicates (same date, amount, description)
    seen = set()
    for i, txn in enumerate(statement.transactions):
        key = (txn.txn_date, txn.amount, txn.description)
        if key in seen:
            result.add_warning(
                "duplicate_txn",
                f"Possible duplicate: {txn.description} ₹{txn.amount}",
            )
        seen.add(key)

    return result
