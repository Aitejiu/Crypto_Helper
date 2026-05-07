from __future__ import annotations

from typer.testing import CliRunner

from crypto_helper import __version__
from crypto_helper.cli import app


def test_help_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Secure Multi-KOL Agent Workspace domain CLI." in result.output


def test_version_command() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output
