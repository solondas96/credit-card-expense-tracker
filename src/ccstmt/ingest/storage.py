"""Storage management for raw and extracted files."""

import hashlib
from datetime import datetime
from pathlib import Path


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def get_raw_path(
    data_dir: Path, issuer: str, message_id: str, attachment_name: str
) -> Path:
    """Get path for storing raw (encrypted) PDF.

    Format: data/raw/<issuer>/<YYYY>/<YYYY-MM-DD>_<message_id>_<safe_filename>.pdf
    """
    today = datetime.now()
    year = str(today.year)
    date_str = today.strftime("%Y-%m-%d")

    # Sanitize filename
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in attachment_name)

    raw_dir = data_dir / "raw" / issuer / year
    raw_dir.mkdir(parents=True, exist_ok=True)

    path = raw_dir / f"{date_str}_{message_id}_{safe_name}"
    return path


def get_extracted_path(data_dir: Path, statement_id: str) -> Path:
    """Get path for storing extracted JSON.

    Format: data/extracted/<statement_id>.json
    """
    extracted_dir = data_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    return extracted_dir / f"{statement_id}.json"


def save_raw_file(
    data_dir: Path,
    issuer: str,
    message_id: str,
    attachment_name: str,
    data: bytes,
) -> Path:
    """Save raw file and return path."""
    path = get_raw_path(data_dir, issuer, message_id, attachment_name)
    path.write_bytes(data)
    return path
