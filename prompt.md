# Master Prompt — Credit Card Statement Pipeline (Gmail → Structured Data)

> Paste everything below this line into your coding agent. Fill in the `<<FILL ME>>` bits first (section 0).

---

## Role

You are a senior Python data engineer. Build a small, production-quality, **local-first** application that connects to my Gmail account (read-only), finds credit card statement emails from multiple banks, downloads the PDF statements, decrypts them, extracts structured data, and loads it into a local analytical database. Every run must pick up **only the new delta**. A UI will be built later, so the core must be a clean library + CLI with a stable data model.

Keep it **simple**: one Python package, one CLI, one DuckDB file, no web server, no Docker requirement, no orchestration frameworks, no agent frameworks.

---

## 0. Inputs I'm providing (fill before running)

- Cards / issuers I hold: `<<FILL ME: e.g. HDFC, ICICI, SBI Card, Axis, Amex>>`
- Backfill start date for the first run: `<<FILL ME: e.g. 2024-01-01>>`
- LLM provider for extraction: `<<FILL ME: anthropic | openai | ollama>>`
- Statements are mostly **password-protected PDFs** (Indian banks). I'll supply each issuer's password via `.env` — never hardcode, never guess.

If anything above is missing, use placeholders and carry on; do not stop to ask.

---

## 1. Scope

**In scope (v1)**
- Gmail OAuth (read-only) with a local token.
- Issuer-driven discovery of statement emails via Gmail search queries.
- Incremental (delta) sync with a durable ledger so nothing is processed twice.
- Download PDF attachments, store raw copies, decrypt with per-issuer passwords.
- Text extraction → LLM-based structured extraction validated against a Pydantic schema.
- Arithmetic reconciliation checks; failures flagged, not dropped.
- Load into DuckDB (statements + transactions), idempotent upserts.
- Simple rule-based merchant normalization + categorization (YAML rules).
- Analytical views + CSV/Parquet export.
- CLI: `auth`, `discover`, `sync`, `reprocess`, `status`, `export`.
- Tests with synthetic fixtures; README with setup steps.

**Out of scope (v1)** — design so these can be added later, but don't build them:
- UI / API server.
- OCR for scanned (image-only) PDFs → mark as `needs_review`.
- Statements delivered as download links instead of attachments → log as `unsupported`.
- Bank-specific deterministic parsers (but leave the plug-in interface for them).
- Gmail push notifications / Pub/Sub.

---

## 2. Tech stack (fixed — don't substitute)

- Python 3.11+, project managed with **uv** (`pyproject.toml`)
- `google-api-python-client`, `google-auth-oauthlib` — Gmail API
- `pikepdf` — PDF decryption
- `pdfplumber` — text extraction (layout-aware)
- `pydantic` v2 — schemas and validation
- `duckdb` — storage and analytics
- `typer` + `rich` — CLI and console output
- `pyyaml`, `python-dotenv`
- LLM SDK for the chosen provider (`anthropic` / `openai` / plain HTTP for `ollama`) behind one interface
- `pytest`, `reportlab` (test fixtures only), `ruff` for lint/format

---

## 3. Architecture

```
Gmail ──► Discovery (per-issuer query) ──► Delta filter (message ledger)
      ──► Download attachment ──► data/raw (bronze, original encrypted PDF)
      ──► Decrypt (pikepdf) ──► Text extract (pdfplumber)
      ──► Redact (mask card numbers) ──► LLM extract → Pydantic model
      ──► Validate / reconcile ──► data/extracted/<statement_id>.json (silver)
      ──► Normalize + categorize ──► DuckDB tables (silver) ──► views (gold)
```

Each stage is a plain function/class with explicit inputs and outputs so stages can be re-run independently (`reprocess` starts from raw files on disk, not from Gmail).

### Repo layout

```
cc-statements/
  pyproject.toml
  README.md
  DECISIONS.md               # assumptions you made, one line each
  .env.example
  .gitignore                 # must exclude data/, secrets/, .env, *.json tokens
  config/
    issuers.yaml             # issuer definitions (no secrets)
    categories.yaml          # merchant → category rules
  src/ccstmt/
    __init__.py
    cli.py                   # typer app
    settings.py              # loads .env + YAML, paths
    gmail/
      auth.py                # OAuth flow, token refresh, invalid_grant handling
      client.py              # thin wrapper: search, get message, get attachment
      discovery.py           # build queries per issuer, suggest new issuers
    ingest/
      ledger.py              # ingested_messages read/write
      sync.py                # delta orchestration
      storage.py             # raw/extracted file paths, sha256
    pdf/
      decrypt.py
      text.py
      redact.py
    extract/
      schema.py              # Pydantic models (see section 6)
      base.py                # Extractor protocol: can_handle(), extract()
      llm.py                 # provider-agnostic LLM extractor
      providers/             # anthropic.py, openai.py, ollama.py
      validate.py            # reconciliation rules
    transform/
      normalize.py           # merchant normalization
      categorize.py          # rule engine from categories.yaml
    db/
      schema.sql
      repo.py                # upserts, queries
      views.sql
    query.py                 # read-only functions returning rows/DataFrames (future UI uses this)
  tests/
    fixtures/                # generated synthetic PDFs + recorded LLM outputs
    ...
  data/                      # gitignored: raw/, extracted/, ccstmt.duckdb
  secrets/                   # gitignored: credentials.json, token.json
```

---

## 4. Configuration

### `config/issuers.yaml`
Do **not** invent real sender addresses. Ship placeholders; I'll fill them using `ccstmt discover`.

```yaml
issuers:
  - id: hdfc                       # short slug, used in paths and IDs
    name: HDFC Bank
    senders: ["<<sender@bank.example>>"]
    subject_patterns: ["statement"] # case-insensitive substrings or regex
    attachment_pattern: ".*\\.pdf$"
    password_env: CC_PWD_HDFC       # env var holding the PDF password (optional)
    enabled: true
```

### `.env.example`
```
GMAIL_CREDENTIALS_PATH=secrets/credentials.json
GMAIL_TOKEN_PATH=secrets/token.json
BACKFILL_SINCE=2024-01-01
SYNC_OVERLAP_DAYS=3
LLM_PROVIDER=anthropic
LLM_MODEL=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
CC_PWD_HDFC=
```

---

## 5. Gmail ingestion & delta logic (the core requirement)

**Auth**
- Scope: `https://www.googleapis.com/auth/gmail.readonly` only.
- Desktop OAuth flow (`InstalledAppFlow.run_local_server`). Token saved to `GMAIL_TOKEN_PATH`, auto-refreshed.
- On `invalid_grant` / expired refresh token, fail with a clear message: "Run `ccstmt auth` to re-authorize." (Google Cloud apps in *Testing* status issue refresh tokens that expire after ~7 days — document this in the README and how to avoid it.)

**Discovery**
- Per enabled issuer, build a query: `from:(a OR b) has:attachment filename:pdf after:<epoch>` plus subject filtering applied client-side with the configured patterns.
- Page through all results (`nextPageToken`). Respect rate limits with exponential backoff on 429/5xx.
- `ccstmt discover --since <date>`: search the inbox for likely statement emails (subjects containing "statement", "card statement", "e-statement", with PDF attachments), group by sender, and print a table of sender / count / sample subject / whether already configured. This is how I'll populate `issuers.yaml`.

**Delta rules**
1. The **message ledger** (`ingested_messages`, keyed by Gmail `message_id` + attachment id) is the source of truth. A message already in the ledger with a terminal success status is never re-downloaded.
2. A per-issuer **watermark** (`sync_state.last_success_epoch`) is an optimization: query `after: watermark − SYNC_OVERLAP_DAYS` to tolerate late-arriving mail and clock skew. First run uses `BACKFILL_SINCE`.
3. Advance the watermark **only** after the issuer's run finishes without unhandled errors.
4. Also dedupe by `file_sha256` of the decrypted PDF (banks resend the same statement) and by `statement_id` (section 7).
5. `sync --dry-run` lists what would be processed without downloading.

**Ledger statuses**: `discovered → downloaded → decrypted → extracted → validated → loaded`, plus terminal/failure states `needs_review`, `decrypt_failed`, `extract_failed`, `unsupported`, `duplicate`. Store the error message. `reprocess --failed` retries everything not `loaded`/`duplicate`/`unsupported`.

**Raw storage**: `data/raw/<issuer>/<YYYY>/<YYYY-MM-DD>_<message_id>_<safe_filename>.pdf` — store the original bytes untouched.

---

## 6. Extraction

### Text
- Decrypt with `pikepdf` using the issuer's password (try empty password first). Wrong/missing password → `decrypt_failed` with a helpful message naming the env var.
- Extract text page-by-page with `pdfplumber` (keep layout). If total extracted text is near-empty → `needs_review` with reason `scanned_pdf_no_text`.

### Redaction before any LLM call
- Mask any 12–19 digit card-number-like sequences (allow spaces/dashes) to `XXXX…<last4>`.
- Never send passwords, and never store full card numbers anywhere — only `card_last4`.

### Pydantic schema (`extract/schema.py`)
```
StatementExtract:
  issuer: str
  card_last4: str               # 4 digits
  card_variant: str | None
  currency: str = "INR"
  statement_date: date
  period_start: date | None
  period_end: date | None
  payment_due_date: date | None
  total_amount_due: Decimal
  minimum_amount_due: Decimal | None
  previous_balance: Decimal | None
  payments_credits: Decimal | None
  purchases_debits: Decimal | None
  fees_charges: Decimal | None      # finance charges, fees, GST
  credit_limit: Decimal | None
  available_credit: Decimal | None
  reward_points_closing: Decimal | None
  transactions: list[TransactionExtract]

TransactionExtract:
  txn_date: date
  posting_date: date | None
  description: str
  amount: Decimal                  # always positive
  direction: "debit" | "credit"
  card_last4: str | None           # add-on cards often appear in the same statement
  original_amount: Decimal | None  # foreign-currency txns
  original_currency: str | None
  is_emi: bool = False
  reference: str | None
```

### LLM extractor (`extract/llm.py`)
- One `LLMProvider` interface (`complete_json(system, user, json_schema) -> dict`) with implementations for anthropic, openai and ollama. Use the provider's structured-output / tool-calling mechanism where available.
- Prompt: give the schema, Indian date and number formats (`DD/MM/YYYY`, `1,23,456.78`, `Cr`/`Dr` suffixes), instruct "extract only what is present, use null when absent, do not compute or infer values, every transaction row must appear exactly once".
- Long statements: send the summary pages for header fields, then chunk transaction pages (e.g. 3–4 pages per call), then merge and de-duplicate rows that span page breaks.
- Validate output with Pydantic; on validation error, retry **once** with the errors fed back. Still failing → `extract_failed`.
- Record `extractor`, `model`, `prompt_version` on every statement.
- Keep the `Extractor` protocol (`can_handle(issuer, text) -> bool`, `extract(text) -> StatementExtract`) so a deterministic per-bank parser can later take priority over the LLM.

### Validation (`extract/validate.py`)
Run and store results; failures set `validation_status = needs_review` but the data **is still loaded** (flagged), never silently dropped:
- `previous_balance − payments_credits + purchases_debits + fees_charges ≈ total_amount_due` (tolerance ₹1.00) when all fields are present.
- Sum of debit transactions ≈ `purchases_debits + fees_charges` (tolerance configurable, report the delta).
- All `txn_date`s fall within the period (±3 days grace).
- `card_last4` is 4 digits; no transaction has amount 0; no duplicate rows (same date, amount, description) unless the PDF actually lists them twice.

---

## 7. Data model (DuckDB, `data/ccstmt.duckdb`)

IDs are deterministic so re-runs are idempotent:
- `statement_id = sha256(issuer | card_last4 | statement_date)[:16]`
- `txn_id = sha256(statement_id | txn_date | amount | direction | normalized_description | occurrence_index)[:16]` — `occurrence_index` disambiguates identical rows within one statement.

Tables:
- `ingested_messages(message_id, attachment_id, issuer, thread_id, received_at, sender, subject, attachment_name, raw_path, file_sha256, statement_id, status, error, first_seen_at, updated_at)` — PK `(message_id, attachment_id)`
- `sync_state(issuer PK, last_success_epoch, last_run_at, last_run_status)`
- `statements(statement_id PK, issuer, card_last4, card_variant, currency, statement_date, period_start, period_end, payment_due_date, total_amount_due, minimum_amount_due, previous_balance, payments_credits, purchases_debits, fees_charges, credit_limit, available_credit, reward_points_closing, source_message_id, file_sha256, extractor, model, prompt_version, validation_status, validation_notes JSON, loaded_at)`
- `transactions(txn_id PK, statement_id FK, issuer, card_last4, txn_date, posting_date, description_raw, merchant, category, category_source, amount_signed, amount, direction, currency, original_amount, original_currency, is_emi, is_international, line_no)`
  - `amount_signed`: debit = positive spend, credit = negative.

Reloading a statement = in one DB transaction, delete its transactions and upsert the statement + new transactions.

Views (`db/views.sql`):
- `v_transactions` — enriched, excludes payments to the card (category `card_payment`) via a flag column, not deletion
- `v_monthly_spend` — month × category × issuer
- `v_card_summary` — per card: statements, total spend, avg monthly spend, latest due date/amount
- `v_top_merchants` — merchant spend and count, last 3/6/12 months
- `v_needs_review` — statements and messages needing attention

---

## 8. Normalization & categorization

- `normalize.py`: uppercase, strip reference numbers / city / country suffixes / long digit runs / payment-gateway prefixes (e.g. `PAYU*`, `RAZ*`, `PYU*`), collapse whitespace → `merchant`.
- `categories.yaml`: ordered rules `{pattern (regex), category}`; first match wins; default `uncategorized`. Seed sensible categories: groceries, food_delivery, dining, fuel, travel, shopping_online, utilities, telecom, subscriptions, entertainment, health, education, insurance, rent, emi, fees_charges, cashback_rewards, card_payment, transfer, uncategorized.
- `category_source = rule | default` (leave room for `llm` and `manual` later).
- Categorization re-runs cheaply over the DB (`ccstmt reprocess --categories-only`) when rules change, without touching Gmail or the LLM.

---

## 9. CLI (`ccstmt`)

| Command | Behaviour |
|---|---|
| `ccstmt auth` | Run OAuth, save token, print the authorized email address |
| `ccstmt discover [--since DATE]` | Suggest statement senders not yet in `issuers.yaml` |
| `ccstmt sync [--issuer ID] [--since DATE] [--dry-run]` | Delta ingest → extract → load; summary table at the end (found / new / loaded / needs_review / failed per issuer) |
| `ccstmt reprocess [--failed \| --statement-id ID \| --issuer ID \| --all] [--categories-only]` | Re-run from raw files on disk; never re-hits Gmail |
| `ccstmt status` | Ledger counts by status, watermarks, last run, items needing review |
| `ccstmt export --table transactions\|statements --format csv\|parquet --out PATH [--from DATE --to DATE]` | Export for analysis / the future UI |

Exit codes: `0` success, `1` partial failures, `2` config/auth errors. Logs go to `data/logs/ccstmt.log` (rotating) plus a concise console view.

---

## 10. Security & privacy (non-negotiable)

- Read-only Gmail scope. No sending, labeling, or deleting mail.
- `secrets/`, `data/`, `.env`, `*.duckdb` and token files are gitignored — verify before finishing.
- Never log or persist full card numbers, PDF passwords, OAuth tokens or API keys. Logs show issuer, message_id, status and counts — never transaction descriptions at INFO level.
- The only outbound network calls are Gmail and the configured LLM provider. With `LLM_PROVIDER=ollama`, nothing leaves the machine except Gmail traffic.
- PDF passwords come only from env vars (optionally OS keyring via `keyring` if trivial to add).

---

## 11. Testing

- `tests/fixtures/make_fixtures.py` generates 2–3 **synthetic** statements with `reportlab` (different layouts, one with an add-on card, one with a foreign-currency transaction, one multi-page) and encrypts them with `pikepdf`.
- A `FakeGmailClient` serving fixture messages, plus recorded LLM JSON responses so tests run offline with no API keys.
- Required tests:
  - Running `sync` twice → second run processes 0 messages, row counts unchanged.
  - Adding one new fixture email → only that one is processed.
  - The same PDF sent in two emails → loaded once, second marked `duplicate`.
  - Wrong password → `decrypt_failed`, other issuers keep going.
  - Reconciliation pass and fail cases; a failing statement is loaded with `needs_review`.
  - Redaction masks 16-digit numbers in various formats.
  - Deterministic IDs are stable across runs; identical transactions in one statement both survive.
  - Categorization rule ordering.
- `ruff check` and `pytest` must pass.

---

## 12. Build plan — work through these milestones in order

After each milestone: run lint + tests, fix failures, then move on. Don't stop to ask me questions; when something is ambiguous, pick the simplest reasonable option and record it as one line in `DECISIONS.md`.

1. **Scaffold** — uv project, layout, settings loader, `.gitignore`, `.env.example`, ruff, empty CLI with `--help`.
2. **Gmail auth + client + discover** — OAuth, token refresh, paginated search with backoff, `ccstmt auth`, `ccstmt discover`.
3. **Ledger + delta sync (download only)** — DuckDB schema, ledger statuses, watermark + overlap logic, raw storage, `--dry-run`, `status`.
4. **PDF layer** — decrypt, text extraction, scanned-PDF detection, redaction.
5. **Extraction** — schema, provider interface + one working provider (the one I chose) + stubs for the others, chunking, retry-on-validation-error.
6. **Validation + load** — reconciliation, deterministic IDs, idempotent upsert, `reprocess`.
7. **Transform + analytics** — normalization, categorization, views, `export`, `query.py`.
8. **Hardening + docs** — full test suite green; README with: Google Cloud project setup (enable Gmail API, OAuth consent screen, Desktop client, download `credentials.json`), the 7-day testing-mode token caveat, filling `issuers.yaml` via `discover`, setting passwords, first backfill, scheduling a daily run with cron, sample DuckDB queries, and how a future UI should consume `query.py` / exports.

## 13. Definition of done

- `uv run ccstmt auth && uv run ccstmt sync` on a fresh clone (with my config) backfills all statements; running `sync` again immediately does nothing new.
- Every statement email ends in exactly one terminal status, visible in `ccstmt status`.
- `transactions` and `statements` are populated, validated, categorized, and queryable through the views.
- No secrets or personal data are tracked by git.
- Tests pass offline. README lets someone set it up end-to-end in under 15 minutes.

At the end, print a short report: what was built, the assumptions in `DECISIONS.md`, and any known limitations.