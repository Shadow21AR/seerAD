from typer import Typer
from rich import print

# Import subcommands
from seerAD.cli import reset as reset_cmd
from seerAD.cli import target as target_cmd
from seerAD.cli import creds as creds_cmd
from seerAD.cli import timewrap as timewrap_cmd
# from seerAD.cli import enum as enum_cmd
# from seerAD.cli import abuse as abuse_cmd
# from seerAD.cli import tasks as tasks_cmd

app = Typer(
    help="SeerAD - Active Directory Attack Framework",
    no_args_is_help=True,
    add_completion=False,
)

# Register CLI commands
app.command("reset")(reset_cmd.reset_session)
app.add_typer(target_cmd.app, name="target", help="Manage targets")
app.add_typer(creds_cmd.app, name="creds", help="Manage credentials")
app.add_typer(timewrap_cmd.app, name="timewrap", help="Time management commands")
# app.add_typer(enum_cmd.app, name="enum", help="Enumeration modules")
# app.add_typer(abuse_cmd.app, name="abuse", help="Privilege abuse techniques")
# app.add_typer(tasks_cmd.app, name="tasks", help="Task queue and execution")

@app.command("version")
def version():
    """Show the SeerAD version."""
    from seerAD.config import VERSION
    print(f"[bold green]SeerAD[/] version [yellow]{VERSION}[/]")