"""loopa CLI root."""

from __future__ import annotations

import typer

from agent_loopa.cli.generate_cmd import generate_command
from agent_loopa.cli.review_cmd import review_command
from agent_loopa.version import __version__

app = typer.Typer(
    name="loopa",
    help="agent-loopa: multi-agent SDLC harness for production-quality code.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.command("generate")(generate_command)
app.command("review")(review_command)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agent-loopa {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


if __name__ == "__main__":
    app()
