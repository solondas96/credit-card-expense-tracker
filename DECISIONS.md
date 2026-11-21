# Design Decisions

This file documents assumptions and trade-offs made during development.

## Milestone 1 (Scaffold)
- **Project structure**: Using `src/` layout with `src/ccstmt/` following Python best practices for packaging.
- **Configuration**: Separate YAML files for issuers and categories; .env for secrets and runtime config.
- **Logging directory**: Pre-created at `logs/` with log files managed by Python's RotatingFileHandler (to be added in milestone 8).
- **CLI framework**: Typer with Rich for console output; structured logging added in milestone 8.

## Milestone 2 (Gmail auth + discovery)
- **OAuth scope**: Read-only `gmail.readonly` enforced; no send/modify/delete permissions.
- **Token storage**: JSON file in `secrets/` with auto-refresh; invalid_grant errors caught with helpful message.
- **Rate limiting**: Exponential backoff on 429/5xx; respects Gmail API quota.
- **Discovery**: Searches for statement keywords in subject and PDF attachments; groups by sender.

## Milestone 3 (Ledger + delta sync)
- **DuckDB**: SQLite-compatible local database for schema simplicity; no external DB dependency.
- **Delta logic**: Watermark-based with SYNC_OVERLAP_DAYS to tolerate late-arriving mail and clock skew.
- **Deduplication**: By Gmail message_id + attachment_id (primary key) and by file SHA256 (content dedup).
- **Terminal statuses**: `loaded`, `duplicate`, `unsupported` are not reprocessed; others can be retried with `reprocess`.
- **Raw storage**: Original encrypted PDFs stored untouched at `data/raw/<issuer>/<year>/<date>_<id>_<name>.pdf`.
- **Status tracking**: Every email ends in exactly one terminal or processing status; errors stored with timestamps.
