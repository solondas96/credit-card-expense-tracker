"""Load extracted statements to database with idempotent upserts."""

import json

from ccstmt.db.ids import statement_id, txn_id
from ccstmt.db.repo import Repository
from ccstmt.extract.schema import StatementExtract


class StatementLoader:
    """Load statements to database."""

    def __init__(self, repo: Repository):
        """Initialize loader."""
        self.repo = repo

    def load_statement(
        self,
        extract: StatementExtract,
        issuer_id: str,
        message_id: str,
        file_sha256: str,
        extractor: str,
        model: str,
        validation_result=None,
    ) -> str:
        """Load extracted statement and transactions to database.

        Returns statement_id on success.
        """
        # Generate deterministic statement ID
        stmt_id = statement_id(issuer_id, extract.card_last4, extract.statement_date)

        # Prepare validation notes
        validation_status = "valid"
        validation_notes = {}
        if validation_result and validation_result.warnings:
            validation_status = "needs_review"
            validation_notes = validation_result.notes

        # Upsert statement
        self.repo.db.execute(
            """
            INSERT INTO statements
            (statement_id, issuer, card_last4, card_variant, currency, statement_date,
             period_start, period_end, payment_due_date, total_amount_due,
             minimum_amount_due, previous_balance, payments_credits, purchases_debits,
             fees_charges, credit_limit, available_credit, reward_points_closing,
             source_message_id, file_sha256, extractor, model, prompt_version,
             validation_status, validation_notes, loaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (statement_id) DO UPDATE SET
                validation_status = ?,
                validation_notes = ?,
                loaded_at = CURRENT_TIMESTAMP
            """,
            [
                stmt_id,
                issuer_id,
                extract.card_last4,
                extract.card_variant,
                extract.currency,
                extract.statement_date,
                extract.period_start,
                extract.period_end,
                extract.payment_due_date,
                float(extract.total_amount_due),
                float(extract.minimum_amount_due) if extract.minimum_amount_due else None,
                float(extract.previous_balance) if extract.previous_balance else None,
                float(extract.payments_credits) if extract.payments_credits else None,
                float(extract.purchases_debits) if extract.purchases_debits else None,
                float(extract.fees_charges) if extract.fees_charges else None,
                float(extract.credit_limit) if extract.credit_limit else None,
                float(extract.available_credit) if extract.available_credit else None,
                float(extract.reward_points_closing)
                if extract.reward_points_closing
                else None,
                message_id,
                file_sha256,
                extractor,
                model,
                "1.0",
                validation_status,
                json.dumps(validation_notes),
                validation_status,
                json.dumps(validation_notes),
            ],
        )

        # Delete existing transactions for this statement (for re-load scenario)
        self.repo.db.execute(
            "DELETE FROM transactions WHERE statement_id = ?", [stmt_id]
        )

        # Insert transactions with deterministic IDs
        occurrence_count = {}

        for txn in extract.transactions:
            # Count occurrences to disambiguate duplicates
            key = (txn.txn_date, txn.amount, txn.description)
            occurrence_count[key] = occurrence_count.get(key, 0)
            occurrence_index = occurrence_count[key]
            occurrence_count[key] += 1

            # Generate transaction ID
            txn_hash_id = txn_id(
                stmt_id,
                txn.txn_date,
                str(txn.amount),
                txn.direction,
                txn.description,
                occurrence_index,
            )

            # Calculate signed amount (debit positive, credit negative)
            if txn.direction == "debit":
                amount_signed = float(txn.amount)
            else:
                amount_signed = -float(txn.amount)

            self.repo.db.execute(
                """
                INSERT INTO transactions
                (txn_id, statement_id, issuer, card_last4, txn_date, posting_date,
                 description_raw, merchant, category, category_source, amount_signed,
                 amount, direction, currency, original_amount, original_currency,
                 is_emi, is_international, line_no)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (txn_id) DO UPDATE SET
                    description_raw = ?,
                    amount_signed = ?,
                    amount = ?,
                    direction = ?
                """,
                [
                    txn_hash_id,
                    stmt_id,
                    issuer_id,
                    extract.card_last4,
                    txn.txn_date,
                    txn.posting_date,
                    txn.description,
                    None,  # merchant (filled in transform phase)
                    None,  # category (filled in transform phase)
                    None,  # category_source
                    amount_signed,
                    float(txn.amount),
                    txn.direction,
                    extract.currency,
                    float(txn.original_amount) if txn.original_amount else None,
                    txn.original_currency,
                    txn.is_emi,
                    False,  # is_international (can be enhanced)
                    None,
                    # For ON CONFLICT DO UPDATE
                    txn.description,
                    amount_signed,
                    float(txn.amount),
                    txn.direction,
                ],
            )

        # Mark message as loaded
        self.repo.update_message_status(
            message_id, "", "loaded", statement_id=stmt_id
        )

        return stmt_id
