"""CLI application using typer."""

from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(help="Credit card statement pipeline.")
console = Console()


@app.command()
def auth() -> None:
    """Authorize Gmail access and save token."""
    console.print("[yellow]Gmail authorization not yet implemented[/yellow]")
    console.print("See milestone 2 for OAuth flow implementation.")
    raise typer.Exit(2)


@app.command()
def discover(since: Optional[str] = None) -> None:
    """Discover statement emails not yet configured."""
    console.print("[yellow]Discovery not yet implemented[/yellow]")
    console.print("See milestone 2 for discovery implementation.")
    raise typer.Exit(2)


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
