"""Deterministic ID generation for idempotent upserts."""

import hashlib
from datetime import date


def statement_id(issuer: str, card_last4: str, statement_date: date) -> str:
    """Generate deterministic statement ID.

    Format: sha256(issuer | card_last4 | statement_date)[:16]
    """
    key = f"{issuer}|{card_last4}|{statement_date}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def txn_id(
    statement_id_val: str,
    txn_date: date,
    amount: str,
    direction: str,
    description: str,
    occurrence_index: int = 0,
) -> str:
    """Generate deterministic transaction ID.

    Format: sha256(statement_id | txn_date | amount | direction |
                   normalized_description | occurrence_index)[:16]
    """
    key = (
        f"{statement_id_val}|{txn_date}|{amount}|{direction}|"
        f"{description}|{occurrence_index}"
    )
    return hashlib.sha256(key.encode()).hexdigest()[:16]
