# cc-statements: Credit Card Statement Pipeline

**Local-first** Python application that connects to Gmail, discovers credit card statements, downloads and decrypts PDFs, extracts structured data with LLM, and loads into a local DuckDB database.

## Quick Start

### Prerequisites
- Python 3.11+ (tested with 3.12)
- `uv` package manager ([install](https://github.com/astral-sh/uv))
- Google Cloud project with Gmail API enabled

### Setup

1. **Clone and install:**
   ```bash
   git clone <repo>
   cd cc-statements
   uv sync
   ```

2. **Configure Google OAuth:**
   - Create a [Google Cloud project](https://console.cloud.google.com/)
   - Enable the Gmail API
   - Create an OAuth 2.0 consent screen (External)
   - Create a Desktop client ID (`Credentials → Create OAuth 2.0 Client ID`)
   - Download credentials as `credentials.json` to `secrets/`

3. **Configure issuers:**
   - Edit `config/issuers.yaml` with your banks' sender addresses (use `ccstmt discover` to find them)
   - For each issuer, set the PDF password in `.env`:
     ```bash
     CC_PWD_HDFC=<password>
     CC_PWD_ICICI=<password>
     ```

4. **Authorize and backfill:**
   ```bash
   uv run ccstmt auth
   uv run ccstmt sync
   ```

## Commands

```bash
uv run ccstmt --help

uv run ccstmt auth              # Authorize Gmail access
uv run ccstmt discover          # Find statement emails not yet configured
uv run ccstmt sync              # Download, decrypt, extract, and load statements
uv run ccstmt reprocess --all   # Reprocess all statements from raw files
uv run ccstmt status            # Show sync status
uv run ccstmt export --help     # Export data to CSV/Parquet
```

## Architecture

```
Gmail ──► Discovery (per-issuer query) ──► Delta filter
   ──► Download attachment ──► Decrypt ──► Text extract
   ──► Redact ──► LLM extract ──► Validate ──► Load to DuckDB
   ──► Normalize + Categorize ──► Analytics views
```

Each stage is independent, allowing re-runs from raw files without re-hitting Gmail.

## Data Model

- **DuckDB** database (`data/ccstmt.duckdb`)
- **Tables:** `ingested_messages`, `sync_state`, `statements`, `transactions`
- **Deterministic IDs** for idempotent upserts
- **Validation status** tracked; failed statements flagged but still loaded

## Configuration

- **`.env`** — Gmail paths, LLM provider, passwords, backfill dates
- **`config/issuers.yaml`** — Bank metadata and search patterns
- **`config/categories.yaml`** — Merchant categorization rules

## Security

- ✓ Read-only Gmail scope
- ✓ Passwords from env vars only
- ✓ No full card numbers or OAuth tokens in logs
- ✓ Encrypted PDFs never decrypted in memory long-term
- ✓ Redaction masks card numbers before LLM calls

## Testing

```bash
uv run pytest tests/
uv run ruff check src/ tests/
```

## Status

**v0.1.0** — Scaffolding complete (Milestone 1). See `DECISIONS.md` for assumptions.

Milestones in progress:
1. ✓ Scaffold
2. Gmail auth + discovery
3. Ledger + delta sync
4. PDF layer
5. Extraction
6. Validation + load
7. Transform + analytics
8. Hardening + docs
