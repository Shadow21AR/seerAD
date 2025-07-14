import typer
from rich import print
from seerAD.core.session import session

app = typer.Typer(help="Session management commands")

@app.command("reset")
def reset_session(confirm: bool = typer.Option(False, "--confirm", "-y", help="Confirm reset without prompt")):
    """
    Reset session data to empty (targets, creds, current context).
    This will clear all targets and credentials from the current session.
    """
    if not confirm:
        print("[yellow][!] This will erase all targets and credentials from memory.[/]")
        confirm_text = typer.prompt("Type 'reset' to confirm")
        if confirm_text.lower() != "reset":
            print("[red]✘ Aborted[/]")
            raise typer.Exit()

    session.reset()
    session.save()
    print("[green][+] Session reset complete[/]")