import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from seerAD.config import LOOT_DIR
from seerAD.core.session import session
from seerAD.core.utils import get_faketime_offset 

console = Console()
timewrap_app = typer.Typer(help="Time synchronization for Kerberos operations")

TIMEWRAP_FILE = LOOT_DIR / "timewrap.json"

def save_timewrap_config(dc_ip: str, offset: str):
    data = {
        "dc_ip": dc_ip,
        "offset": offset,
        "set_at": datetime.utcnow().isoformat()
    }
    with open(TIMEWRAP_FILE, "w") as f:
        json.dump(data, f, indent=2)


def clear_env_vars():
    os.environ.pop("LD_PRELOAD", None)
    os.environ.pop("FAKETIME", None)


def reset():
    clear_env_vars()
    if TIMEWRAP_FILE.exists():
        TIMEWRAP_FILE.unlink()
    console.print("✔ Timewrap reset to system time", style="green")

@timewrap_app.command("set")
def set_time(dc_ip: Optional[str] = typer.Argument(None, help="DC IP to sync time from")):
    """
    Set timewrap using skew from DC.
    Creates/updates timewrap file and restarts the application.
    """

    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        raise typer.Exit()

    if not dc_ip:
        dc_ip = session.current_target.get("ip")
        if not dc_ip:
            console.print("[red]No DC IP provided or found in current target.[/]")
            raise typer.Exit()
    
    if os.getenv("LD_PRELOAD") and "libfaketime" in os.getenv("LD_PRELOAD", ""):
        console.print("[yellow]Already under faketime. Reset it first.[/]")
        raise typer.Exit()
    

    console.print(f"[blue]Fetching time from DC {dc_ip}...[/]")
    offset = get_faketime_offset(dc_ip)

    if offset is None:
        console.print("[red]✘ Failed to fetch or calculate time offset from DC[/]")
        raise typer.Exit()

    # Save the new configuration
    save_timewrap_config(dc_ip, offset)
    console.print(f"[green]✓ Timewrap offset set:[/] {offset}")
    
    # Restart the application to apply the new time settings
    console.print("[yellow]Restarting with new time settings...[/]")
    os.execv(sys.executable, [sys.executable] + sys.argv)


@timewrap_app.command("reset")
def reset_time():
    """
    Reset timewrap to use real system time.
    Cleans up environment, removes timewrap file, and restarts the application.
    """
    if TIMEWRAP_FILE.exists() or "LD_PRELOAD" in os.environ:
        # Clear environment variables
        clear_env_vars()
        
        # Remove the timewrap file if it exists
        if TIMEWRAP_FILE.exists():
            try:
                TIMEWRAP_FILE.unlink()
                console.print("[green]✓ Removed timewrap configuration[/]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not remove timewrap file: {e}[/]")
        
        # Restart the application
        console.print("[yellow]Restarting with system time...[/]")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        console.print("[yellow]No active timewrap to reset.[/]")


@timewrap_app.command("status")
def timewrap_status():
    """
    Show current timewrap status.
    """
    if TIMEWRAP_FILE.exists():
        with open(TIMEWRAP_FILE, "r") as f:
            data = json.load(f)
        console.print("[green]✔ Timewrap is active:[/]")
        console.print(f"  DC IP   : {data.get('dc_ip')}")
        console.print(f"  Offset  : {data.get('offset')}")
        console.print(f"  Set At  : {data.get('set_at')}")
    else:
        console.print("[yellow]No timewrap is currently set[/]")

# Expose as app
app = timewrap_app
