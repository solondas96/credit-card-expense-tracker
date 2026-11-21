"""Pydantic schemas for extracted statement data."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TransactionExtract(BaseModel):
    """Extracted transaction data."""

    txn_date: date
    posting_date: Optional[date] = None
    description: str
    amount: Decimal = Field(decimal_places=2)
    direction: str  # "debit" or "credit"
    card_last4: Optional[str] = None
    original_amount: Optional[Decimal] = Field(None, decimal_places=2)
    original_currency: Optional[str] = None
    is_emi: bool = False
    reference: Optional[str] = None
    category: Optional[str] = None  # Set by categorizer
    category_source: Optional[str] = None  # "rule" or "default"


class StatementExtract(BaseModel):
    """Extracted statement data."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "issuer": "hdfc",
                "card_last4": "1234",
                "currency": "INR",
                "statement_date": "2024-11-22",
                "total_amount_due": "15000.00",
                "transactions": [
                    {
                        "txn_date": "2024-11-15",
                        "description": "Amazon purchase",
                        "amount": "2500.00",
                        "direction": "debit",
                    }
                ],
            }
        }
    }

    issuer: str
    card_last4: str
    card_variant: Optional[str] = None
    currency: str = "INR"
    statement_date: date
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    payment_due_date: Optional[date] = None
    total_amount_due: Decimal = Field(decimal_places=2)
    minimum_amount_due: Optional[Decimal] = Field(None, decimal_places=2)
    previous_balance: Optional[Decimal] = Field(None, decimal_places=2)
    payments_credits: Optional[Decimal] = Field(None, decimal_places=2)
    purchases_debits: Optional[Decimal] = Field(None, decimal_places=2)
    fees_charges: Optional[Decimal] = Field(None, decimal_places=2)
    credit_limit: Optional[Decimal] = Field(None, decimal_places=2)
    available_credit: Optional[Decimal] = Field(None, decimal_places=2)
    reward_points_closing: Optional[Decimal] = Field(None, decimal_places=2)
    transactions: list[TransactionExtract]
