"""Read-only analytics queries for exports and UI."""

from datetime import date
from pathlib import Path

import duckdb


class Analytics:
    """Read-only analytics interface."""

    def __init__(self, db_path: Path):
        """Initialize analytics reader."""
        self.db_path = db_path
        self.db = duckdb.connect(str(db_path), read_only=True)
        self._ensure_views()

    def _ensure_views(self):
        """Create views if they don't exist."""
        views_path = Path(__file__).parent / "db" / "views.sql"
        if views_path.exists():
            with open(views_path) as f:
                self.db.execute(f.read())

    def monthly_spend(
        self, issuer: str = None, from_date: date = None, to_date: date = None
    ) -> list[dict]:
        """Get monthly spending by category."""
        query = "SELECT * FROM v_monthly_spend WHERE 1=1"
        params = []

        if issuer:
            query += " AND issuer = ?"
            params.append(issuer)
        if from_date:
            query += " AND month >= ?"
            params.append(from_date)
        if to_date:
            query += " AND month <= ?"
            params.append(to_date)

        query += " ORDER BY month DESC"
        return self.db.execute(query, params).fetchall()

    def card_summary(self) -> list[dict]:
        """Get summary for each card."""
        return self.db.execute(
            "SELECT * FROM v_card_summary ORDER BY issuer"
        ).fetchall()

    def top_merchants(
        self, limit: int = 20, days: int = 90
    ) -> list[dict]:
        """Get top merchants by spend (last N days)."""
        query = """
        SELECT *
        FROM v_top_merchants
        WHERE last_used >= CURRENT_DATE - INTERVAL ? DAY
        ORDER BY total_spend DESC
        LIMIT ?
        """
        return self.db.execute(query, [days, limit]).fetchall()

    def needs_review(self) -> list[dict]:
        """Get all items needing manual review."""
        return self.db.execute("SELECT * FROM v_needs_review").fetchall()

    def transactions(
        self,
        issuer: str = None,
        category: str = None,
        from_date: date = None,
        to_date: date = None,
    ) -> list[dict]:
        """Get transactions with optional filters."""
        query = "SELECT * FROM v_transactions WHERE is_card_payment = FALSE"
        params = []

        if issuer:
            query += " AND issuer = ?"
            params.append(issuer)
        if category:
            query += " AND category = ?"
            params.append(category)
        if from_date:
            query += " AND txn_date >= ?"
            params.append(from_date)
        if to_date:
            query += " AND txn_date <= ?"
            params.append(to_date)

        query += " ORDER BY txn_date DESC"
        return self.db.execute(query, params).fetchall()

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
