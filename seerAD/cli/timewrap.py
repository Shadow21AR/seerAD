import typer
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from rich.console import Console
from seerAD.config import ROOT_DIR
from seerAD.core.utils import get_faketime_string
from seerAD.core.session import session
from typing import Optional

console = Console()
timewrap_app = typer.Typer(help="Time synchronization for Kerberos operations")

TIMEWRAP_FILE = ROOT_DIR / "timewrap.json"


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


def restart_seerad(with_faketime: bool = False):
    """
    Restart SeerAD with or without faketime env.
    """
    python_path = sys.executable
    args = [python_path, "-m", "seerAD.main"]
    env = os.environ.copy()

    if with_faketime and TIMEWRAP_FILE.exists():
        try:
            with open(TIMEWRAP_FILE, "r") as f:
                data = json.load(f)
                faketime = data.get("faketime")
                if faketime:
                    env["FAKETIME"] = faketime
                    env["SEERAD_FAKE_STARTED"] = "1"
                    libfaketime = "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1"
                    if not Path(libfaketime).exists():
                        console.print("[red]libfaketime not found! Make sure it's installed.[/]")
                        return
                    env["LD_PRELOAD"] = libfaketime
        except Exception as e:
            console.print(f"[red]✘ Failed to load faketime:[/] {e}")

    elif not with_faketime:
        env.pop("FAKETIME", None)
        env.pop("SEERAD_FAKE_STARTED", None)
        env.pop("LD_PRELOAD", None)

    console.print("[cyan]Restarting SeerAD...[/]")
    os.execvpe(python_path, args, env)


@timewrap_app.command("set")
def set_time(dc_ip: Optional[str] = typer.Argument(None, help="DC IP to sync time from")):
    """
    Set system time skew based on target DC IP.
    """
    if not dc_ip:
        dc_ip = session.current_target.get("ip")

    if not dc_ip:
        console.print("[red]No DC IP provided or active target.[/]")
        return

    if TIMEWRAP_FILE.exists():
        console.print("[yellow]Timewrap already set. Reset before setting again.[/]")
        return

    console.print(f"[blue]Fetching time from DC {dc_ip}...[/]")
    faketime_str = get_faketime_string(dc_ip)
    if not faketime_str:
        console.print("[red]Failed to fetch time from DC.[/]")
        return

    save_timewrap_config(dc_ip, faketime_str)
    console.print(f"[green]✔ Timewrap set:[/] {faketime_str}")
    restart_seerad(with_faketime=True)


@timewrap_app.command("reset")
def reset_time():
    """
    Reset time skew override and return to system time.
    """
    if TIMEWRAP_FILE.exists():
        reset_timewrap_config()
        console.print("[green]✔ Timewrap reset. Returning to system time.[/]")
    else:
        console.print("[blue]No active timewrap to reset.[/]")

    restart_seerad(with_faketime=False)


@timewrap_app.command("status")
def status():
    """
    Show current timewrap status.
    """
    if TIMEWRAP_FILE.exists():
        with open(TIMEWRAP_FILE, "r") as f:
            data = json.load(f)
            console.print(f"[green]Timewrap active:[/] {data['faketime']} (set at {data['set_at']})")
    else:
        console.print("[blue]No active timewrap.[/]")


app = timewrap_app
