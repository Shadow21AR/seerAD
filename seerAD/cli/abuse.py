import typer
from typing import List, Optional
from rich.console import Console
from seerAD.tool_handler.impacket_helper import run_impacket
from seerAD.tool_handler.helper import run_command
from seerAD.core.session import session

console = Console()
abuse_app = typer.Typer(help="Abuse commands", add_completion=False)

COMMANDS = {
    # Impacket tools
    "userspns":         lambda m, a: run_impacket("GetUserSPNs", m, a + ["-request"]),
}

@abuse_app.command("list")
def list_modules():
    """List available abuse modules"""
    console.print("[cyan bold]Available Abuse Modules:[/]")
    cmds = ", ".join(sorted(COMMANDS.keys()))

    console.print(f"[green]{cmds}[/]")

@abuse_app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run_abuse(
    ctx: typer.Context,
    module: str = typer.Argument(..., help="Abuse module name (e.g., userspns)"),
    method: Optional[str] = typer.Argument("anon", help="Auth method (ticket, password, ntlm, aes128, aes256, anon)")
):
    """Run a specific enum module with auth method and optional args."""
    try:
        if session.current_credential.get("ticket") and method == "anon":
            method = "ticket"
        run_command(module, method, ctx.args, COMMANDS)
    except Exception as e:
        console.print(f"[red][!] Error: {e}[/]")
        return

app = abuse_app