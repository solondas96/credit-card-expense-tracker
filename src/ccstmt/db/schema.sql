-- DuckDB schema for credit card statements

-- Tracks ingested messages and their processing status
CREATE TABLE IF NOT EXISTS ingested_messages (
    message_id TEXT NOT NULL,
    attachment_id TEXT NOT NULL,
    issuer TEXT NOT NULL,
    thread_id TEXT,
    received_at TIMESTAMP,
    sender TEXT,
    subject TEXT,
    attachment_name TEXT,
    raw_path TEXT,
    file_sha256 TEXT,
    statement_id TEXT,
    status TEXT NOT NULL DEFAULT 'discovered',
    -- Status values: discovered, downloaded, decrypted, extracted, validated, loaded,
    -- needs_review, decrypt_failed, extract_failed, unsupported, duplicate
    error TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, attachment_id)
);

-- Tracks sync state per issuer (watermarks and last run info)
CREATE TABLE IF NOT EXISTS sync_state (
    issuer TEXT PRIMARY KEY,
    last_success_epoch TEXT,
    last_run_at TIMESTAMP,
    last_run_status TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extracted statement data
CREATE TABLE IF NOT EXISTS statements (
    statement_id TEXT PRIMARY KEY,
    issuer TEXT NOT NULL,
    card_last4 TEXT NOT NULL,
    card_variant TEXT,
    currency TEXT DEFAULT 'INR',
    statement_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    payment_due_date DATE,
    total_amount_due DECIMAL(10, 2) NOT NULL,
    minimum_amount_due DECIMAL(10, 2),
    previous_balance DECIMAL(10, 2),
    payments_credits DECIMAL(10, 2),
    purchases_debits DECIMAL(10, 2),
    fees_charges DECIMAL(10, 2),
    credit_limit DECIMAL(10, 2),
    available_credit DECIMAL(10, 2),
    reward_points_closing DECIMAL(10, 2),
    source_message_id TEXT,
    file_sha256 TEXT,
    extractor TEXT,
    model TEXT,
    prompt_version TEXT,
    validation_status TEXT,
    validation_notes JSON,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transaction data
CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    statement_id TEXT NOT NULL REFERENCES statements(statement_id),
    issuer TEXT NOT NULL,
    card_last4 TEXT,
    txn_date DATE NOT NULL,
    posting_date DATE,
    description_raw TEXT,
    merchant TEXT,
    category TEXT,
    category_source TEXT,
    amount_signed DECIMAL(10, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    direction TEXT NOT NULL,
    currency TEXT DEFAULT 'INR',
    original_amount DECIMAL(10, 2),
    original_currency TEXT,
    is_emi BOOLEAN DEFAULT FALSE,
    is_international BOOLEAN DEFAULT FALSE,
    line_no INTEGER
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ingested_messages_status ON ingested_messages(status);
CREATE INDEX IF NOT EXISTS idx_ingested_messages_issuer ON ingested_messages(issuer);
CREATE INDEX IF NOT EXISTS idx_ingested_messages_file_sha256 ON ingested_messages(file_sha256);
CREATE INDEX IF NOT EXISTS idx_statements_issuer_date ON statements(issuer, statement_date);
CREATE INDEX IF NOT EXISTS idx_transactions_statement_id ON transactions(statement_id);
CREATE INDEX IF NOT EXISTS idx_transactions_issuer ON transactions(issuer);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
