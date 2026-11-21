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
    console.print("[yellow]Sync not yet implemented[/yellow]")
    console.print("See milestone 3 for sync implementation.")
    raise typer.Exit(2)


@app.command()
def reprocess(
    failed: bool = typer.Option(False, help="Reprocess failed items"),
    statement_id: Optional[str] = None,
    issuer: Optional[str] = None,
    all: bool = typer.Option(False, help="Reprocess all statements"),
    categories_only: bool = typer.Option(False, help="Only reprocess categorization"),
) -> None:
    """Reprocess statements from raw files."""
    console.print("[yellow]Reprocess not yet implemented[/yellow]")
    console.print("See milestone 6 for reprocess implementation.")
    raise typer.Exit(2)


@app.command()
def status() -> None:
    """Show sync status and counts."""
    console.print("[yellow]Status not yet implemented[/yellow]")
    console.print("See milestone 3 for status implementation.")
    raise typer.Exit(2)


@app.command()
def export(
    table: str = typer.Option(..., help="transactions or statements"),
    format: str = typer.Option("csv", help="csv or parquet"),
    out: str = typer.Option(..., help="Output file path"),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> None:
    """Export data for analysis."""
    console.print("[yellow]Export not yet implemented[/yellow]")
    console.print("See milestone 7 for export implementation.")
    raise typer.Exit(2)


@app.callback()
def main(version: bool = typer.Option(None, "--version", help="Show version")) -> None:
    """Credit card statement pipeline."""
    if version:
        import ccstmt
        console.print(f"cc-statements {ccstmt.__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
