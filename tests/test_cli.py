"""CLI tests."""

from typer.testing import CliRunner

from ccstmt.cli import app

runner = CliRunner()


def test_cli_help():
    """Test CLI help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Credit card statement pipeline" in result.stdout
    assert "auth" in result.stdout


def test_auth_requires_credentials():
    """Test that auth command requires credentials file."""
    result = runner.invoke(app, ["auth"])
    assert result.exit_code == 2
    assert "credentials" in result.stdout.lower()
