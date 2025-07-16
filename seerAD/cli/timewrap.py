import typer
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from seerAD.config import LOOT_DIR
from seerAD.core.utils import get_faketime_string
from seerAD.core.session import session
from typing import Optional

console = Console()
timewrap_app = typer.Typer(help="Time synchronization for Kerberos operations")

TIMEWRAP_FILE = LOOT_DIR / "timewrap.json"


def save_timewrap_config(dc_ip: str, faketime: str):
    data = {
        "dc_ip": dc_ip,
        "faketime": faketime,
        "set_at": datetime.utcnow().isoformat()
    }
    with open(TIMEWRAP_FILE, "w") as f:
        json.dump(data, f, indent=2)


def reset_timewrap_config():
    if TIMEWRAP_FILE.exists():
        TIMEWRAP_FILE.unlink()


@timewrap_app.command("set")
def set_time(dc_ip: Optional[str] = typer.Argument(None, help="DC IP to sync time from")):
    """
    Set system time skew based on target DC IP.
    """
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    if not dc_ip:
        dc_ip = session.current_target.get("ip")

    if TIMEWRAP_FILE.exists():
        console.print("[yellow]Timewrap already set. Updating it.[/]")

    console.print(f"[blue]Fetching time from DC {dc_ip}...[/]")
    faketime_str = get_faketime_string(dc_ip)
    if not faketime_str:
        console.print("[red]Failed to fetch time from DC.[/]")
        return

    save_timewrap_config(dc_ip, faketime_str)
    console.print(f"[green]✔ Timewrap set:[/] {faketime_str}")


@timewrap_app.command("reset")
def reset_time():
    """
    Reset timewrap to use system time.
    """
    if TIMEWRAP_FILE.exists():
        reset_timewrap_config()
        console.print("[green]✔ Timewrap reset to use system time[/]")
    else:
        console.print("[yellow]No timewrap is currently set[/]")


@timewrap_app.command("status")
def status():
    """
    Show current timewrap status.
    """
    if TIMEWRAP_FILE.exists():
        with open(TIMEWRAP_FILE, "r") as f:
            data = json.load(f)
            console.print("[green]Timewrap is active:[/]")
            console.print(f"  DC IP: {data.get('dc_ip')}")
            console.print(f"  Fake time: {data.get('faketime')}")
            console.print(f"  Set at: {data.get('set_at')}")
    else:
        console.print("[yellow]No timewrap is currently set[/]")


app = timewrap_app
