import shutil
import typer
from rich import print
from seerAD.core.session import session
from seerAD.config import LOOT_DIR

def reset_session(
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt")
):
    """
    Reset the entire session, removing all targets, credentials, and session data.

    This action is irreversible!
    """
    if not confirm:
        print("[bold red][!] WARNING: This will permanently delete ALL session data![/]")
        print("[red]Includes all targets, credentials, and session info.[/]")
        confirm_text = typer.prompt("\nType 'DELETE ALL' to confirm")
        if confirm_text.strip() != "DELETE ALL":
            print("[red]✘ Reset aborted[/]")
            return

    try:
        for target_dir in LOOT_DIR.glob("*"):
            if target_dir.is_dir() and target_dir.name != "reports":
                shutil.rmtree(target_dir, ignore_errors=True)

        session_file = LOOT_DIR / "session.json"
        session_file.unlink(missing_ok=True)

        session.reset()

        print("[green]✓ Session reset complete[/]")
        print("[dim]All targets and credentials have been removed.[/]")
    except Exception as e:
        print(f"[red]✘ Error during reset: {e}[/]")
        return