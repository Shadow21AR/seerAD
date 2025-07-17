import typer
from typing import List, Optional
from rich.console import Console
from seerAD.enum import run_command, list_commands

console = Console()
enum_app = typer.Typer(help="Enumeration commands", add_completion=False)

@enum_app.command("list")
def list_modules():
    """List available enumeration modules"""
    console.print("[cyan bold]Available Enum Modules:[/]")
    cmds = ", ".join(sorted(list_commands().keys()))
    console.print(f"[green]{cmds}[/]")

@enum_app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run_enum(
    ctx: typer.Context,
    module: str = typer.Argument(..., help="Enum module name (e.g., smb)"),
    method: Optional[str] = typer.Argument("anon", help="Auth method (ticket, password, hash, anon)")
):
    """Run a specific enum module with auth method and optional args."""
    try:
        run_command(module, method, ctx.args)
    except Exception as e:
        console.print(f"[red][!] Error: {e}[/]")
        return

app = enum_app