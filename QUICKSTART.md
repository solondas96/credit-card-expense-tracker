# Quick Start Guide

## Setup (5 minutes)

1. **Add your LLM API key** to `.env`:
   ```bash
   # For Anthropic (recommended):
   ANTHROPIC_API_KEY=sk-ant-...
   
   # OR for OpenAI:
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-proj-...
   ```

2. **Add credit card passwords** to `.env`:
   ```bash
   CC_PWD_HDFC=password123
   CC_PWD_ICICI=password456
   # ... one per issuer
   ```

3. **Authorize Gmail** (opens browser):
   ```bash
   source $HOME/.local/bin/env
   cd /Users/solondas/Desktop/Projects/expese-tracker
   uv run ccstmt auth
   ```
   You'll see: `✓ Authorized: your.email@gmail.com`

4. **Find your banks** (discovers senders in your inbox):
   ```bash
   uv run ccstmt discover
   ```
   Displays table of sender emails found.

5. **Configure issuers** (edit `config/issuers.yaml`):
   ```yaml
   issuers:
     - id: hdfc
       name: HDFC Bank
       senders: ["hdfc.bank@email.com"]  # From discover output
       subject_patterns: ["statement"]
       attachment_pattern: ".*\\.pdf$"
       password_env: CC_PWD_HDFC
       enabled: true
   ```

6. **Backfill historical statements**:
   ```bash
   uv run ccstmt sync
   ```
   Downloads, decrypts, extracts, validates → Database

7. **Check status**:
   ```bash
   uv run ccstmt status
   ```
   Shows message counts and items needing review.

## Running Daily

**Option A: Manual cron**
```bash
# Every day at 6 AM
0 6 * * * cd /Users/solondas/Desktop/Projects/expese-tracker && source $HOME/.local/bin/env && uv run ccstmt sync >> logs/ccstmt.log 2>&1
```

**Option B: At login (macOS)**
```bash
# Create ~/Library/LaunchAgents/com.local.ccstmt.plist
# Or use `launchctl` to register a LaunchAgent
```

## Troubleshooting

**"Gmail authorization expired"**
→ Run `uv run ccstmt auth` again (7-day Testing-status token limit)

**"PDF is encrypted but no password provided"**
→ Check `CC_PWD_*` env var matches issuer ID in `config/issuers.yaml`

**"No JSON found in response"**
→ Check LLM_PROVIDER and API key are set in `.env`

**"No new senders found"**
→ Your inbox may not have statement emails. Use `--since 2020-01-01` to search back further.

## Next Steps

- Run extraction daily with cron
- Complete Milestone 6 (integrate load → database)
- Set up analytics views for spending insights
- Export to CSV for personal finance tools

Questions? Check [README.md](README.md) or [BUILD_SUMMARY.md](BUILD_SUMMARY.md).
