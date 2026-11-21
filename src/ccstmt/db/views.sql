-- Analytical views for credit card statements

-- Enriched transactions view (excludes internal card payments)
CREATE VIEW IF NOT EXISTS v_transactions AS
SELECT
    t.txn_id,
    t.statement_id,
    t.issuer,
    t.card_last4,
    t.txn_date,
    t.posting_date,
    t.description_raw,
    t.merchant,
    t.category,
    t.category_source,
    t.amount,
    t.direction,
    t.currency,
    t.original_amount,
    t.original_currency,
    t.is_emi,
    t.is_international,
    s.statement_date,
    s.card_variant,
    -- Flag internal card payments
    CASE
        WHEN t.category = 'card_payment' THEN TRUE
        ELSE FALSE
    END AS is_card_payment
FROM transactions t
JOIN statements s ON t.statement_id = s.statement_id
ORDER BY t.txn_date DESC;

-- Monthly spending by category and issuer
CREATE VIEW IF NOT EXISTS v_monthly_spend AS
SELECT
    DATE_TRUNC('month', t.txn_date)::DATE AS month,
    t.issuer,
    t.card_last4,
    t.category,
    t.direction,
    SUM(t.amount) AS total_amount,
    COUNT(*) AS txn_count,
    AVG(t.amount) AS avg_amount,
    MIN(t.amount) AS min_amount,
    MAX(t.amount) AS max_amount
FROM transactions t
WHERE t.category != 'card_payment'
GROUP BY
    DATE_TRUNC('month', t.txn_date),
    t.issuer,
    t.card_last4,
    t.category,
    t.direction
ORDER BY month DESC, t.issuer, t.category;

-- Card summary (overview per card)
CREATE VIEW IF NOT EXISTS v_card_summary AS
SELECT
    s.issuer,
    s.card_last4,
    s.card_variant,
    COUNT(DISTINCT s.statement_id) AS statement_count,
    MIN(s.statement_date) AS first_statement,
    MAX(s.statement_date) AS latest_statement,
    SUM(CASE WHEN t.direction = 'debit' AND t.category != 'card_payment'
        THEN t.amount ELSE 0 END) AS total_spend,
    COUNT(DISTINCT CASE WHEN t.direction = 'debit' THEN t.txn_id END)
        AS debit_count,
    COUNT(DISTINCT CASE WHEN t.direction = 'credit' THEN t.txn_id END)
        AS credit_count,
    MAX(s.total_amount_due) AS latest_balance_due,
    MAX(s.payment_due_date) AS latest_due_date,
    SUM(CASE WHEN t.category = 'emi' THEN 1 ELSE 0 END) AS emi_txn_count
FROM statements s
LEFT JOIN transactions t ON s.statement_id = t.statement_id
GROUP BY s.issuer, s.card_last4, s.card_variant
ORDER BY s.issuer, s.card_last4;

-- Top merchants by spend
CREATE VIEW IF NOT EXISTS v_top_merchants AS
SELECT
    t.merchant,
    t.category,
    t.issuer,
    COUNT(*) AS txn_count,
    SUM(t.amount) AS total_spend,
    AVG(t.amount) AS avg_spend,
    MAX(t.txn_date) AS last_used
FROM transactions t
WHERE t.category != 'card_payment' AND t.merchant IS NOT NULL
GROUP BY t.merchant, t.category, t.issuer
ORDER BY total_spend DESC;

-- Items needing manual review
CREATE VIEW IF NOT EXISTS v_needs_review AS
SELECT
    im.message_id,
    im.issuer,
    im.status,
    im.error,
    im.sender,
    im.subject,
    im.updated_at,
    s.statement_id,
    s.statement_date,
    s.validation_status,
    s.validation_notes
FROM ingested_messages im
LEFT JOIN statements s ON im.statement_id = s.statement_id
WHERE
    im.status IN ('needs_review', 'decrypt_failed', 'extract_failed')
    OR s.validation_status = 'needs_review'
ORDER BY im.updated_at DESC;
