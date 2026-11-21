"""Gmail API client wrapper."""

import base64
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ccstmt.gmail.auth import get_authenticated_service, get_authorized_email


class GmailClient:
    """Thin wrapper around Gmail API with retry logic."""

    def __init__(self, credentials_path, token_path):
        """Initialize Gmail client."""
        self.creds = get_authenticated_service(credentials_path, token_path)
        self.service = build("gmail", "v1", credentials=self.creds)

    def get_authorized_email(self) -> str:
        """Get the authorized email address."""
        return get_authorized_email(self.creds, self.service)

    def search_messages(self, query: str, max_results: int = 100):
        """Search for messages matching a query.

        Yields message IDs with exponential backoff on 429/5xx.
        """
        page_token = None
        retry_count = 0
        max_retries = 5

        while True:
            try:
                results = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=query,
                        pageToken=page_token,
                        maxResults=min(max_results, 100),
                    )
                    .execute()
                )

                for message in results.get("messages", []):
                    yield message["id"]

                # Move to next page
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

                retry_count = 0  # Reset on success

            except HttpError as e:
                if e.resp.status in (429, 500, 502, 503, 504):
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    wait_time = 2 ** retry_count
                    print(
                        f"Rate limited (status {e.resp.status}), "
                        f"waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise

    def get_message(self, message_id: str, format: str = "full") -> dict:
        """Get a single message by ID."""
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
            .execute()
        )

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Get attachment data by message and attachment ID."""
        attachment = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

        data = attachment.get("data", "")
        if data:
            return base64.urlsafe_b64decode(data)
        return b""
