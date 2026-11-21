# Design Decisions

This file documents assumptions and trade-offs made during development.

## Milestone 1 (Scaffold)
- **Project structure**: Using `src/` layout with `src/ccstmt/` following Python best practices for packaging.
- **Configuration**: Separate YAML files for issuers and categories; .env for secrets and runtime config.
- **Logging directory**: Pre-created at `logs/` with log files managed by Python's RotatingFileHandler (to be added in hardening phase).
- **CLI framework**: Typer with Rich for console output; structured logging added in hardening phase.

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

## Milestone 4 (PDF layer)
- **Decryption**: pikepdf with per-issuer password from env vars; tries empty password first.
- **Text extraction**: pdfplumber with layout preservation; page-by-page concatenation.
- **Scanned detection**: >50% empty pages or <100 chars total → `needs_review` with reason `scanned_pdf_no_text`.
- **Redaction**: Mask 12-19 digit sequences (card numbers) to `XXXX…<last4>` before LLM calls; never log full card numbers.

## Milestone 5 (Extraction + LLM)
- **Pydantic schemas**: Strict validation; `StatementExtract` and `TransactionExtract` with explicit types.
- **Provider interface**: Pluggable architecture (Anthropic, OpenAI, Ollama); easy to add more.
- **Retry logic**: Retry once on validation error with error feedback; still fail → `extract_failed`.
- **Validation**: Reconciliation checks (balance, debit sum, date range) are warnings, not blockers; `needs_review` flag set but data loaded.

## Milestone 6+ (Validation + load, Transform, Analytics)
- **Deterministic IDs**: SHA256-based, stable across runs → idempotent upserts (no duplicate rows on re-run).
- **Idempotent loading**: ON CONFLICT DO UPDATE for statements and transactions; delete old transactions on reload.
- **Normalization**: Planned for transform phase (merchant cleanup, gateway prefix removal).
- **Categorization**: Rule-based with YAML config; `category_source` distinguishes rule vs. default vs. future LLM.
- **Views**: Planned analytical views (v_transactions excludes card payments, v_monthly_spend, v_card_summary, etc.).
