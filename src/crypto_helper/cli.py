from __future__ import annotations

import typer

from crypto_helper import __version__

app = typer.Typer(
    name="crypto-helper",
    help="Secure Multi-KOL Agent Workspace domain CLI.",
    no_args_is_help=True,
    invoke_without_command=True,
)


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the crypto-helper version and exit.",
        is_eager=True,
    ),
) -> None:
    """Run crypto-helper commands."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()


def main() -> None:
    app()
