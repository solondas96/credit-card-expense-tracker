"""Statement email discovery."""

import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

from ccstmt.gmail.client import GmailClient


def build_query(
    issuer: dict, since_date: Optional[str] = None, overlap_days: int = 3
) -> str:
    """Build Gmail search query for an issuer."""
    senders = issuer.get("senders", [])
    sender_query = " OR ".join(f'from:"{s}"' for s in senders if s)

    # Date filtering
    if since_date:
        date_part = f" after:{since_date}"
    else:
        date_part = ""

    return f"({sender_query}){date_part} has:attachment filename:pdf"


def discover_new_senders(
    client: GmailClient, since_date: Optional[str] = None
) -> dict:
    """Discover statement emails not yet in issuers.yaml.

    Returns dict of sender -> (count, sample_subject, sample_date)
    """
    # Look for common statement keywords
    keywords = ["statement", "card statement", "e-statement", "account statement"]
    keyword_query = " OR ".join(f'subject:{kw}' for kw in keywords)
    query = f"({keyword_query}) has:attachment filename:pdf"

    if since_date:
        query += f" after:{since_date}"

    senders = defaultdict(lambda: {"count": 0, "subject": "", "date": ""})

    for message_id in client.search_messages(query):
        message = client.get_message(message_id, format="metadata")
        headers = message.get("payload", {}).get("headers", [])

        sender = ""
        subject = ""
        internal_date = message.get("internalDate", "0")

        for header in headers:
            if header["name"] == "From":
                sender = header["value"]
            elif header["name"] == "Subject":
                subject = header["value"]

        if sender:
            senders[sender]["count"] += 1
            if not senders[sender]["subject"]:
                senders[sender]["subject"] = subject
            if not senders[sender]["date"]:
                ts = int(internal_date) // 1000
                senders[sender]["date"] = datetime.fromtimestamp(ts).strftime(
                    "%Y-%m-%d"
                )

    return dict(senders)


def suggest_new_issuers(
    client: GmailClient, configured_senders: set, since_date: Optional[str] = None
) -> list:
    """Find unconfigured senders that look like banks."""
    discovered = discover_new_senders(client, since_date)
    unconfigured = {}

    for sender, info in discovered.items():
        # Extract email domain
        match = re.search(r"<(.+?)>", sender)
        email = match.group(1) if match else sender
        domain = email.split("@")[-1] if "@" in email else email

        # Skip if already configured
        if email in configured_senders or domain in configured_senders:
            continue

        unconfigured[sender] = info

    return unconfigured
