"""CLI application using typer."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ccstmt.gmail.client import GmailClient
from ccstmt.gmail.discovery import suggest_new_issuers
from ccstmt.settings import settings

app = typer.Typer(help="Credit card statement pipeline.")
console = Console()


@app.command()
def auth() -> None:
    """Authorize Gmail access and save token."""
    try:
        from googleapiclient.discovery import build

        from ccstmt.gmail.auth import get_authenticated_service, get_authorized_email

        console.print("[bold cyan]Starting Gmail authorization...[/bold cyan]")
        creds = get_authenticated_service(
            settings.gmail_credentials_path, settings.gmail_token_path
        )
        service = build("gmail", "v1", credentials=creds)
        email = get_authorized_email(creds, service)

        console.print(f"[bold green]✓ Authorized[/bold green]: {email}")
        raise typer.Exit(0)

    except FileNotFoundError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise typer.Exit(2)
    except ValueError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise typer.Exit(2)
    except Exception as e:
        console.print(f"[bold red]✗ Authorization failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def discover(since: Optional[str] = None) -> None:
    """Discover statement emails not yet configured."""
    try:
        client = GmailClient(settings.gmail_credentials_path, settings.gmail_token_path)

        # Collect configured senders
        configured_senders = set()
        for issuer in settings.issuers:
            for sender in issuer.get("senders", []):
                if sender and sender != "<<sender@bank.example>>":
                    configured_senders.add(sender)

        console.print("[bold cyan]Searching for statement emails...[/bold cyan]")
        unconfigured = suggest_new_issuers(client, configured_senders, since)

        if not unconfigured:
            console.print("[bold green]✓ No new senders found[/bold green]")
            raise typer.Exit(0)

        # Display results in a table
        table = Table(title="Unconfigured Statement Senders")
        table.add_column("Sender", style="cyan")
        table.add_column("Count", justify="right", style="magenta")
        table.add_column("Sample Subject", style="green")
        table.add_column("Latest Date", style="yellow")

        for sender, info in unconfigured.items():
            table.add_row(
                sender,
                str(info["count"]),
                info.get("subject", "")[:50],
                info.get("date", ""),
            )

        console.print(table)
        console.print("[bold]Add these to config/issuers.yaml[/bold]")
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[bold red]✗ Discovery failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def sync(
    issuer: Optional[str] = None,
    since: Optional[str] = None,
    dry_run: bool = typer.Option(False, help="Preview what would be processed"),
) -> None:
    """Sync and ingest credit card statements."""
    try:
        from ccstmt.db.repo import Repository
        from ccstmt.ingest.sync import SyncOrchestrator
        from ccstmt.logging_config import setup_logging

        logger = setup_logging(settings.logs_dir)
        logger.info(
            f"Starting sync: issuer={issuer}, since={since}, dry_run={dry_run}"
        )

        repo = Repository(settings.db_path)
        client = GmailClient(settings.gmail_credentials_path, settings.gmail_token_path)
        orchestrator = SyncOrchestrator(repo, client, settings.data_dir, settings)

        # Filter issuers
        issuers_to_sync = [
            i
            for i in settings.issuers
            if i.get("enabled", True) and (not issuer or i["id"] == issuer)
        ]

        if not issuers_to_sync:
            console.print("[yellow]No enabled issuers configured[/yellow]")
            raise typer.Exit(1)

        console.print(
            f"[bold cyan]Syncing {len(issuers_to_sync)} issuer(s)"
            f"{' (dry-run)' if dry_run else ''}...[/bold cyan]"
        )

        all_summary = {"found": 0, "new": 0, "downloaded": 0, "needs_review": 0, "failed": 0}
        issuer_results = []

        for issuer_config in issuers_to_sync:
            summary = orchestrator.sync_issuer(issuer_config, since, dry_run)
            issuer_results.append((issuer_config["id"], summary))

            for key in all_summary:
                all_summary[key] += summary.get(key, 0)

        # Display results table
        table = Table(title="Sync Summary")
        table.add_column("Issuer", style="cyan")
        table.add_column("Found", justify="right", style="blue")
        table.add_column("New", justify="right", style="green")
        table.add_column("Downloaded", justify="right", style="magenta")
        table.add_column("Needs Review", justify="right", style="yellow")
        table.add_column("Failed", justify="right", style="red")

        for issuer_id, summary in issuer_results:
            table.add_row(
                issuer_id,
                str(summary["found"]),
                str(summary["new"]),
                str(summary["downloaded"]),
                str(summary["needs_review"]),
                str(summary["failed"]),
            )

        console.print(table)
        console.print(
            f"[bold]Total:[/bold] {all_summary['found']} found, "
            f"{all_summary['new']} new, {all_summary['downloaded']} downloaded"
        )

        logger.info(
            f"Sync completed: found={all_summary['found']}, "
            f"new={all_summary['new']}, downloaded={all_summary['downloaded']}, "
            f"needs_review={all_summary['needs_review']}, failed={all_summary['failed']}"
        )

        repo.close()
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[bold red]✗ Sync failed:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def reprocess(
    failed: bool = typer.Option(False, help="Reprocess failed items"),
    statement_id: Optional[str] = None,
    issuer: Optional[str] = None,
    all: bool = typer.Option(False, help="Reprocess all statements"),
    categories_only: bool = typer.Option(False, help="Only reprocess categorization"),
) -> None:
    """Reprocess statements from raw files or categorize only."""
    try:
        from ccstmt.db.repo import Repository
        from ccstmt.transform.categorize import Categorizer

        repo = Repository(settings.db_path)

        if categories_only:
            # Re-categorize all transactions without re-extracting
            console.print("[bold cyan]Re-categorizing transactions...[/bold cyan]")

            categorizer = Categorizer(
                settings.config_dir / "categories.yaml"
            )

            # Get all transactions
            txns = repo.db.execute(
                "SELECT txn_id, description_raw FROM transactions"
            ).fetchall()

            updated = 0
            for txn_id, desc in txns:
                category, source = categorizer.categorize(desc)
                repo.db.execute(
                    "UPDATE transactions "
                    "SET category = ?, category_source = ? "
                    "WHERE txn_id = ?",
                    [category, source, txn_id],
                )
                updated += 1

            console.print(
                f"[bold green]✓ Categorized {updated} transactions[/bold green]"
            )

        elif failed:
            # Re-extract failed messages
            console.print(
                "[yellow]Reprocess --failed not yet fully implemented[/yellow]"
            )
            console.print(
                "Use --categories-only to re-categorize, or implement full "
                "re-extraction from raw PDFs."
            )

        else:
            console.print("[yellow]Full reprocess from raw PDFs not yet implemented[/yellow]")
            console.print(
                "Currently supports --categories-only. "
                "Full re-extraction coming soon."
            )

        repo.close()
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[bold red]✗ Reprocess failed:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show sync status and counts."""
    try:
        from ccstmt.db.repo import Repository

        repo = Repository(settings.db_path)

        counts = repo.get_message_counts_by_status()
        needs_review = repo.get_messages_needing_review()

        # Display status table
        table = Table(title="Message Status Counts")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right", style="green")

        for status in [
            "discovered",
            "downloaded",
            "decrypted",
            "extracted",
            "validated",
            "loaded",
            "needs_review",
            "decrypt_failed",
            "extract_failed",
            "unsupported",
            "duplicate",
        ]:
            count = counts.get(status, 0)
            table.add_row(status, str(count))

        console.print(table)

        if needs_review:
            console.print("\n[bold yellow]Items Needing Review:[/bold yellow]")
            review_table = Table()
            review_table.add_column("Message ID", style="cyan")
            review_table.add_column("Status", style="yellow")
            review_table.add_column("Error", style="red")

            for msg_id, att_id, issuer, subject, status, error in needs_review[:10]:
                review_table.add_row(msg_id[:8], status, error or "(no error)")

            console.print(review_table)

        repo.close()
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[bold red]✗ Status check failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def export(
    table: str = typer.Option(..., help="transactions or statements or view_name"),
    format: str = typer.Option("csv", help="csv or parquet"),
    out: str = typer.Option(..., help="Output file path"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> None:
    """Export data to CSV or Parquet for analysis."""
    try:
        from pathlib import Path

        import duckdb

        db = duckdb.connect(str(settings.db_path), read_only=True)

        # Validate table name
        valid_tables = [
            "transactions",
            "statements",
            "v_transactions",
            "v_monthly_spend",
            "v_card_summary",
            "v_top_merchants",
            "v_needs_review",
        ]

        if table not in valid_tables:
            console.print(
                f"[bold red]✗ Invalid table.[/bold red] "
                f"Use one of: {', '.join(valid_tables)}"
            )
            raise typer.Exit(2)

        # Build query
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []

        if from_date and table in ["transactions", "v_transactions"]:
            query += " AND txn_date >= ?"
            params.append(from_date)
        if to_date and table in ["transactions", "v_transactions"]:
            query += " AND txn_date <= ?"
            params.append(to_date)

        query += " ORDER BY txn_date DESC" if "txn" in table else ""

        # Execute
        result = db.execute(query, params)

        # Export
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            result.write_csv(str(out_path))
        elif format == "parquet":
            result.write_parquet(str(out_path))
        else:
            console.print(f"[bold red]✗ Unknown format: {format}[/bold red]")
            raise typer.Exit(2)

        console.print(f"[bold green]✓ Exported to {out_path}[/bold green]")
        db.close()
        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[bold red]✗ Export failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.callback()
def main(version: bool = typer.Option(None, "--version", help="Show version")) -> None:
    """Credit card statement pipeline."""
    if version:
        import ccstmt
        console.print(f"cc-statements {ccstmt.__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
