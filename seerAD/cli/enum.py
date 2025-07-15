import typer
from typing import List, Optional
from rich.console import Console
from seerAD.enum import get_enum_module, load_enum_modules

console = Console()
enum_app = typer.Typer(help="Enumeration commands", add_completion=False)

@enum_app.command("list")
def list_modules():
    """List available enumeration modules"""
    load_enum_modules()
    console.print("[cyan bold]Available Enum Modules:[/]")
    for name in sorted(get_enum_module.__globals__['ENUM_MODULES'].keys()):
        console.print(f" - [green]{name}[/]")

@enum_app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run_enum(
    ctx: typer.Context,
    module: str = typer.Argument(..., help="Enum module name (e.g., smb)"),
    method: Optional[str] = typer.Argument(None, help="Auth method (ticket, password, hash, anon)")
):
    """Run a specific enum module with auth method and optional args."""
    load_enum_modules()
    try:
        run_fn = get_enum_module(module)
        if not method:
            console.print("[red][!] Error: No auth method specified.[/]")
            console.print("[yellow]Usage: [/][green]seerAD enum run <module> <method> \[args][/]")
            console.print("[yellow]Available methods: [/][green]ticket, password, hash, anon[/]")
            console.print("[yellow]Example: [/][green]seerAD enum run smb ticket --shares[/]")
            return
        run_fn(method, ctx.args)
    except Exception as e:
        console.print(f"[red][!] Error: {e}[/]")

app = enum_app