"""Delta sync orchestration."""

from datetime import datetime, timedelta
from typing import Optional

from ccstmt.db.repo import Repository
from ccstmt.gmail.client import GmailClient
from ccstmt.gmail.discovery import build_query
from ccstmt.ingest.storage import compute_sha256, save_raw_file


class SyncOrchestrator:
    """Orchestrates delta sync: download, decrypt, extract, load."""

    def __init__(self, repo: Repository, client: GmailClient, data_dir, settings):
        """Initialize orchestrator."""
        self.repo = repo
        self.client = client
        self.data_dir = data_dir
        self.settings = settings

    def sync_issuer(
        self,
        issuer: dict,
        since_date: Optional[str] = None,
        dry_run: bool = False,
    ) -> dict:
        """Sync a single issuer using delta logic.

        Returns summary: {found, new, downloaded, needs_review, failed}
        """
        issuer_id = issuer["id"]
        summary = {"found": 0, "new": 0, "downloaded": 0, "needs_review": 0, "failed": 0}

        # Get sync state to determine query date
        sync_state = self.repo.get_sync_state(issuer_id)
        last_epoch = sync_state.get("last_success_epoch")

        # Determine query start date with overlap
        if since_date:
            query_date = since_date
        elif last_epoch:
            # Go back SYNC_OVERLAP_DAYS to catch late-arriving mail
            last_dt = datetime.fromisoformat(last_epoch)
            overlap_dt = last_dt - timedelta(days=self.settings.sync_overlap_days)
            query_date = overlap_dt.strftime("%Y-%m-%d")
        else:
            # First run: backfill from BACKFILL_SINCE
            query_date = self.settings.backfill_since

        # Build query and search
        query = build_query(issuer, query_date)

        for message_id in self.client.search_messages(query):
            summary["found"] += 1

            # Check if already processed
            if self.repo.message_has_terminal_status(message_id, None):
                continue

            try:
                message = self.client.get_message(message_id, format="full")
                self._process_message(
                    message_id, message, issuer, dry_run, summary
                )

            except Exception as e:
                summary["failed"] += 1
                if not dry_run:
                    self.repo.update_message_status(
                        message_id,
                        "",
                        "extract_failed",
                        error=str(e),
                    )

        # Update watermark after successful run
        if not dry_run and (summary["new"] > 0 or summary["found"] > 0):
            self.repo.update_sync_state(
                issuer_id, datetime.now().isoformat(), "success"
            )

        return summary

    def _process_message(
        self, message_id: str, message: dict, issuer: dict, dry_run: bool, summary: dict
    ):
        """Process a single message: extract metadata, download attachment."""
        payload = message.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        thread_id = message.get("threadId")
        received_at = int(message.get("internalDate", 0)) // 1000
        received_at = datetime.fromtimestamp(received_at).isoformat()
        sender = headers.get("From", "")
        subject = headers.get("Subject", "")

        # Find PDF attachments
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("filename", "").endswith(".pdf"):
                attachment_id = part.get("body", {}).get("attachmentId")
                attachment_name = part.get("filename", "")

                if not attachment_id:
                    continue

                # Check for duplicates
                if self.repo.message_exists(message_id, attachment_id):
                    if self.repo.message_has_terminal_status(message_id, attachment_id):
                        summary["needs_review"] += 1
                    continue

                summary["new"] += 1

                if dry_run:
                    continue

                # Download and store
                try:
                    attachment_data = self.client.get_attachment(
                        message_id, attachment_id
                    )
                    file_sha256 = compute_sha256(attachment_data)

                    # Check for SHA256 duplicates (same PDF sent twice)
                    if self.repo.file_sha256_exists(file_sha256):
                        self.repo.add_message(
                            message_id,
                            attachment_id,
                            issuer["id"],
                            thread_id,
                            received_at,
                            sender,
                            subject,
                            attachment_name,
                        )
                        self.repo.update_message_status(
                            message_id, attachment_id, "duplicate", file_sha256=file_sha256
                        )
                        summary["needs_review"] += 1
                        continue

                    # Save raw file
                    raw_path = save_raw_file(
                        self.data_dir,
                        issuer["id"],
                        message_id,
                        attachment_name,
                        attachment_data,
                    )

                    self.repo.add_message(
                        message_id,
                        attachment_id,
                        issuer["id"],
                        thread_id,
                        received_at,
                        sender,
                        subject,
                        attachment_name,
                    )
                    self.repo.update_message_status(
                        message_id,
                        attachment_id,
                        "downloaded",
                        raw_path=str(raw_path),
                        file_sha256=file_sha256,
                    )

                    summary["downloaded"] += 1

                except Exception as e:
                    self.repo.add_message(
                        message_id,
                        attachment_id,
                        issuer["id"],
                        thread_id,
                        received_at,
                        sender,
                        subject,
                        attachment_name,
                    )
                    self.repo.update_message_status(
                        message_id,
                        attachment_id,
                        "decrypt_failed",
                        error=str(e),
                    )
                    summary["failed"] += 1
