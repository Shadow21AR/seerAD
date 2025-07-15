import typer
import shutil
import subprocess
from typing import Optional, List
from rich.console import Console
from rich.table import Table, box
from seerAD.core.session import session
from seerAD.config import LOOT_DIR
from pathlib import Path
import os
from seerAD.core.utils import get_faketime_string

console = Console()
creds_app = typer.Typer(help="Credential management commands")
fetch_app = typer.Typer(help="Fetch derived artifacts like tickets, certs, etc.")

def display_credentials(creds: List[dict]):
    if not creds:
        console.print("[yellow]No credentials found.[/]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Username", style="cyan")
    table.add_column("Domain", style="cyan")
    table.add_column("Password", style="cyan")
    table.add_column("NTLM", style="cyan")
    table.add_column("AES", style="cyan")
    table.add_column("Ticket", style="cyan")
    table.add_column("Cert", style="cyan")
    table.add_column("Token", style="cyan")
    table.add_column("Notes", style="cyan")

    for cred in creds:
        table.add_row(
            f'[bold green]{cred.get("username", "N/A")}*[/]' if session.current_credential and cred.get("username") == session.current_credential.get("username") else cred.get("username", "N/A"),
            f'[green]{cred.get("domain") or (session.current_target.get("domain", "N/A") if session.current_target else "N/A")}[/]',
            "✔" if cred.get("password") else "✘",
            "✔" if cred.get("ntlm") else "✘",
            "✔" if cred.get("aes") else "✘",
            "✔" if cred.get("ticket") else "✘",
            "✔" if cred.get("cert") else "✘",
            "✔" if cred.get("token") else "✘",
            (str(cred.get("notes") or "")[:20] + "...") if len(str(cred.get("notes") or "")) > 20 else str(cred.get("notes") or "")
        )

    console.print(table)

def run_gettgt(domain, username, password=None, ntlm=None, dc_ip=None):
    if not shutil.which("getTGT.py"):
        console.print("→ Install Impacket and ensure it's accessible: [bold green]pipx install impacket[/]")
        return False, "getTGT.py not found in PATH"

    faketime_str = get_faketime_string(dc_ip) if dc_ip else None
    if not faketime_str:
        return False, f"Unable to fetch time from {dc_ip} for faketime"

    temp_ccache = f"/tmp/{username}_ccache"
    env = os.environ.copy()
    env["KRB5CCNAME"] = temp_ccache
    user_spec = f"{domain}/{username}"
    cmd = ["faketime", faketime_str, "getTGT.py"]

    if password:
        user_spec += f":{password}"
    elif ntlm:
        cmd += ["-hashes", f":{ntlm}"]
    else:
        return False, "No password or NTLM hash provided"

    cmd += [user_spec]

    if dc_ip:
        cmd += ["-dc-ip", dc_ip]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, env=env)

        if Path(temp_ccache).exists():
            label = session.current_target_label
            out_dir = LOOT_DIR / label / "tickets"
            out_dir.mkdir(parents=True, exist_ok=True)

            final_path = out_dir / f"{username}.ccache"
            shutil.move(temp_ccache, final_path)

            return True, str(final_path)
        else:
            return False, f"Expected ticket at {temp_ccache} not found"

    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode() if e.stderr else str(e)

@creds_app.command("add")
def creds_add(
    username: str = typer.Argument(...),
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    password: Optional[str] = typer.Option(None, "--password", "-p"),
    ntlm: Optional[str] = typer.Option(None, "--ntlm", "-n"),
    aes: Optional[str] = typer.Option(None, "--aes"),
    ticket: Optional[str] = typer.Option(None, "--ticket"),
    cert: Optional[str] = typer.Option(None, "--cert"),
    token: Optional[str] = typer.Option(None, "--token"),
    notes: Optional[str] = typer.Option("", "--notes", "-N"),
):
    """Add a new credential to the current target."""
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    if not any([password, ntlm, aes, ticket, cert, token]):
        console.print("[red]Provide at least one credential secret (password, hash, ticket, etc.)[/]")
        return

    existing = session.get_credentials(username=username)
    if any(c.get("username") == username for c in existing):
        console.print(f"[yellow]✘ Credential for user '{username}' already exists.[/]")
        return

    added = session.add_credential(
        session.current_target_label,
        username=username,
        domain=domain,
        password=password,
        ntlm=ntlm,
        aes=aes,
        ticket=ticket,
        cert=cert,
        token=token,
        notes=notes
    )

    if added:
        console.print(f"[green]✔ Credential added for:[/] {username}")
    else:
        console.print(f"[red]✘ Failed to add credential for:[/] {username}")

@creds_app.command("list")
def creds_list():
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    creds = session.get_credentials()
    display_credentials(creds)

@creds_app.command("info")
def creds_info():
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    cred = session.current_credential
    if not cred:
        console.print("[yellow]No credential selected. Use 'creds use' first.[/]")
        return

    table = Table(box=box.ROUNDED, show_header=False)
    for k, v in cred.items():
        table.add_row(f"[cyan]{k}[/]", str(v) if v else "-")

    console.print(f"\n[bold]Current credential for target [cyan]{session.current_target_label}[/][/]")
    console.print(table)

@creds_app.command("use")
def creds_use(
    username: str = typer.Argument(..., help="Username to select")
):
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    success = session.use_credential(username)
    if success:
        console.print(f"[green]✔ Selected credential:[/] {username}")
    else:
        console.print("[red]Credential not found.[/]")

@creds_app.command("set")
def creds_set(
    field: str = typer.Argument(..., help="Field to update (password, ntlm, aes, domain, notes, etc.)"),
    value: str = typer.Argument(..., help="New value (use '' to clear field)"),
):
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    cred = session.current_credential
    if not cred:
        console.print("[yellow]No credential selected. Use 'creds use' first.[/]")
        return

    field = field.lower()
    if field not in {"password", "ntlm", "aes", "ticket", "cert", "token", "domain", "notes"}:
        console.print("[red]Invalid field. Allowed: password, ntlm, aes, ticket, cert, token, domain, notes[/]")
        return

    clean_value = None if value.strip() == "" else value
    updated = session.update_credential(session.current_target_label, cred["username"], **{field: clean_value})
    if updated:
        console.print(f"[green]✔ Updated {field}[/]")
    else:
        console.print(f"[red]✘ Failed to update {field}[/]")

@creds_app.command("del")
def creds_del(
    username: str = typer.Argument(..., help="Username to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")
):
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        return

    creds = session.get_credentials(username=username)
    if not creds:
        console.print("[yellow]No credential found for user:[/] {username}")
        return

    if not force:
        confirm = typer.confirm(f"Delete credentials for '{username}'?")
        if not confirm:
            console.print("[yellow]Cancelled.[/]")
            return

    deleted = session.delete_credential(session.current_target_label, username)
    if deleted:
        if session.current_credential is None:
            console.print(f"[yellow]Deleted selected credential. No credential is now active.[/]")
        console.print(f"[green]✔ Deleted credentials for:[/] {username}")
    else:
        console.print("[red]✘ Failed to delete credential[/]")

@fetch_app.command("ticket")
def fetch_ticket():
    target = session.current_target
    cred = session.current_credential

    if not target or not cred:
        console.print("[red]No active target or selected credential.[/]")
        return

    username = cred.get("username")
    domain = cred.get("domain") or target.get("domain")
    password = cred.get("password")
    ntlm = cred.get("ntlm")

    if not username or not domain:
        console.print("[red]Missing username or domain.[/]")
        return

    if not password and not ntlm:
        console.print("[red]Credential must have either password or NTLM hash.[/]")
        return

    label = session.current_target_label
    out_dir = LOOT_DIR / label / "tickets"
    out_dir.mkdir(parents=True, exist_ok=True)
    ticket_path = out_dir / f"{username}.ccache"

    success, err = run_gettgt(domain, username, password, ntlm, target.get("ip"))
    if not success:
        console.print(f"[red]Ticket fetch failed:[/] {err}")
        return

    session.update_credential(label, username, ticket=str(ticket_path))
    console.print(f"[green]✔ Ticket saved:[/] {ticket_path}")
    console.print(f"[green]✔ Credential updated with ticket path[/]")

creds_app.add_typer(fetch_app, name="fetch")
app = creds_app