"""Database repository for statements and transactions."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb


class Repository:
    """DuckDB repository for statements and transactions."""

    def __init__(self, db_path: Path):
        """Initialize repository and create schema."""
        self.db_path = db_path
        self.db = duckdb.connect(str(db_path))
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema from SQL file."""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path) as f:
            self.db.execute(f.read())

        # Create analytical views
        views_path = Path(__file__).parent / "views.sql"
        if views_path.exists():
            with open(views_path) as f:
                self.db.execute(f.read())

    def message_exists(self, message_id: str, attachment_id: str) -> bool:
        """Check if a message is already in the ledger."""
        result = self.db.execute(
            """
            SELECT 1 FROM ingested_messages
            WHERE message_id = ? AND attachment_id = ?
            """,
            [message_id, attachment_id],
        ).fetchall()
        return len(result) > 0

    def message_has_terminal_status(self, message_id: str, attachment_id: str) -> bool:
        """Check if a message has a terminal status (won't be reprocessed)."""
        terminal_statuses = ["loaded", "duplicate", "unsupported"]
        result = self.db.execute(
            """
            SELECT status FROM ingested_messages
            WHERE message_id = ? AND attachment_id = ?
            """,
            [message_id, attachment_id],
        ).fetchall()

        if not result:
            return False
        return result[0][0] in terminal_statuses

    def add_message(
        self,
        message_id: str,
        attachment_id: str,
        issuer: str,
        thread_id: str,
        received_at: datetime,
        sender: str,
        subject: str,
        attachment_name: str,
    ) -> None:
        """Add a message to the ledger."""
        self.db.execute(
            """
            INSERT INTO ingested_messages
            (message_id, attachment_id, issuer, thread_id, received_at, sender, subject,
             attachment_name, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'discovered')
            ON CONFLICT (message_id, attachment_id)
            DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            """,
            [
                message_id,
                attachment_id,
                issuer,
                thread_id,
                received_at,
                sender,
                subject,
                attachment_name,
            ],
        )

    def update_message_status(
        self,
        message_id: str,
        attachment_id: str,
        status: str,
        raw_path: Optional[str] = None,
        file_sha256: Optional[str] = None,
        statement_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update message status and metadata."""
        self.db.execute(
            """
            UPDATE ingested_messages
            SET status = ?, raw_path = ?, file_sha256 = ?, statement_id = ?, error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE message_id = ? AND attachment_id = ?
            """,
            [status, raw_path, file_sha256, statement_id, error, message_id, attachment_id],
        )

    def get_sync_state(self, issuer: str) -> dict:
        """Get sync state for an issuer."""
        result = self.db.execute(
            """
            SELECT last_success_epoch, last_run_at, last_run_status
            FROM sync_state WHERE issuer = ?
            """,
            [issuer],
        ).fetchall()

        if result:
            return {
                "last_success_epoch": result[0][0],
                "last_run_at": result[0][1],
                "last_run_status": result[0][2],
            }
        return {"last_success_epoch": None, "last_run_at": None, "last_run_status": None}

    def update_sync_state(
        self, issuer: str, last_success_epoch: str, status: str = "success"
    ) -> None:
        """Update sync state for an issuer."""
        self.db.execute(
            """
            INSERT INTO sync_state (issuer, last_success_epoch, last_run_at, last_run_status)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT (issuer) DO UPDATE SET
                last_success_epoch = ?,
                last_run_at = CURRENT_TIMESTAMP,
                last_run_status = ?
            """,
            [issuer, last_success_epoch, status, last_success_epoch, status],
        )

    def get_message_counts_by_status(self) -> dict:
        """Get counts of messages by status."""
        result = self.db.execute(
            """
            SELECT status, COUNT(*) FROM ingested_messages
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()
        return {row[0]: row[1] for row in result}

    def get_messages_needing_review(self) -> list:
        """Get messages with needs_review or failed statuses."""
        result = self.db.execute(
            """
            SELECT message_id, attachment_id, issuer, subject, status, error
            FROM ingested_messages
            WHERE status IN ('needs_review', 'decrypt_failed', 'extract_failed')
            ORDER BY updated_at DESC
            """
        ).fetchall()
        return result

    def file_sha256_exists(self, sha256: str) -> bool:
        """Check if a file with this SHA256 is already ingested (deduplication)."""
        result = self.db.execute(
            """
            SELECT 1 FROM ingested_messages
            WHERE file_sha256 = ?
            """,
            [sha256],
        ).fetchall()
        return len(result) > 0

    def close(self):
        """Close database connection."""
        if self.db:
            self.db.close()
