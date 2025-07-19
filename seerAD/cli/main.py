import typer
from rich.console import Console
from seerAD.cli.abuse import abuse_callback
from seerAD.cli.enum import enum_callback

console = Console()

app = typer.Typer(
    help="SeerAD - Active Directory Attack Framework",
    no_args_is_help=True,
    add_completion=False,
)

@app.command("version")
def version():
    """Show the SeerAD version."""
    from seerAD.config import VERSION
    console.print(f"[bold green]SeerAD[/] version [yellow]{VERSION}[/]")

@app.command("enum", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}, help="Enumeration commands")
def enum(ctx: typer.Context):
    return enum_callback(ctx)

@app.command("abuse", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}, help="Abuse commands")
def abuse(ctx: typer.Context):
    return abuse_callback(ctx)

# Import subcommands
from seerAD.cli import reset as reset_cmd
from seerAD.cli import target as target_cmd
from seerAD.cli import creds as creds_cmd
from seerAD.cli import timewrap as timewrap_cmd
# from seerAD.cli import smart as smart_cmd

# Register CLI commands
app.command("reset")(reset_cmd.reset_session)
app.add_typer(target_cmd.app, name="target", help="Manage targets")
app.add_typer(creds_cmd.app, name="creds", help="Manage credentials")
app.add_typer(timewrap_cmd.app, name="timewrap", help="Time management commands")

# app.command("smart")(smart_cmd.app)