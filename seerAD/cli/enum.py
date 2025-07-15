import typer
from rich.console import Console
from seerAD.enum import load_enum_modules, get_enum_module

console = Console()
enum_app = typer.Typer(help="Enumeration commands")

@enum_app.command("run")
def enum_run(module: str, args: str = typer.Argument(None)):
    """Run a specific enum module"""
    load_enum_modules()
    try:
        run_fn = get_enum_module(module)
        run_fn(args)
    except ValueError as e:
        console.print(f"[red]{e}[/]")

@enum_app.command("list")
def enum_list():
    """List all available enum modules"""
    load_enum_modules()
    console.print("[cyan bold]Available Enum Modules:[/]")
    for name in sorted(get_enum_module.__globals__['ENUM_MODULES'].keys()):
        console.print(f" - [green bold]{name}[/]")

app = enum_app