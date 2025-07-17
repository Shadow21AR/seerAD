import typer, os, shutil, subprocess
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table, box

from seerAD.core.session import session
from seerAD.config import LOOT_DIR
import seerAD.core.utils as utils

console = Console()
creds_app = typer.Typer(help="Credential management commands")

def display_credentials(creds: List[dict]):
    if not creds:
        console.print("[yellow]No credentials found.[/]")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Username", style="cyan")
    table.add_column("Domain", style="cyan")
    table.add_column("Password", style="cyan")
    table.add_column("NTLM", style="cyan")
    table.add_column("AES-128", style="cyan")
    table.add_column("AES-256", style="cyan")
    table.add_column("Ticket", style="cyan")
    table.add_column("Cert", style="cyan")
    table.add_column("Notes", style="cyan")

    for cred in creds:
        table.add_row(
            f'[bold green]{cred.get("username", "N/A")}*[/]' if session.current_credential and cred.get("username") == session.current_credential.get("username") else cred.get("username", "N/A"),
            f'[green]{cred.get("domain") or (session.current_target.get("domain", "N/A") if session.current_target else "N/A")}[/]',
            "✔" if cred.get("password") else "✘",
            "✔" if cred.get("ntlm") else "✘",
            "✔" if cred.get("aes128") else "✘",
            "✔" if cred.get("aes256") else "✘",
            "✔" if cred.get("ticket") else "✘",
            "✔" if cred.get("cert") else "✘",
            (str(cred.get("notes") or "")[:20] + "...") if len(str(cred.get("notes") or "")) > 20 else str(cred.get("notes") or "")
        )

    console.print(table)

@creds_app.command("add")
def creds_add(
    username: str = typer.Argument(...),
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    password: Optional[str] = typer.Option(None, "--password", "-p"),
    ntlm: Optional[str] = typer.Option(None, "--ntlm", "-n"),
    aes128: Optional[str] = typer.Option(None, "--aes128"),
    aes256: Optional[str] = typer.Option(None, "--aes256"),
    ticket: Optional[str] = typer.Option(None, "--ticket"),
    cert: Optional[str] = typer.Option(None, "--cert"),
    notes: Optional[str] = typer.Option("", "--notes", "-N"),
):
    """Add a new credential to the current target."""
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    if not any([password, ntlm, aes128, aes256, ticket, cert]):
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
        aes128=aes128,
        aes256=aes256,
        ticket=ticket,
        cert=cert,
        notes=notes
    )

    if added:
        console.print(f"[green]✔ Credential added for:[/] {username}")
    else:
        console.print(f"[red]✘ Failed to add credential for:[/] {username}")
    
    if not session.current_credential:
        session.use_credential(username)
        console.print(f"[green]✔ Selected credential:[/] {username}")

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
        if k == 'domain':
            v = v or session.current_target.get("domain", "N/A")
        table.add_row(f"[cyan]{k}[/]", f"[green]{str(v)}[/]" if v else "[red]-[/]")

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
    field: str = typer.Argument(..., help="Field to update (password, ntlm, aes128, aes256, ticket, cert, domain, notes, etc.)"),
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
    if field not in {"password", "ntlm", "aes128", "aes256", "ticket", "cert", "domain", "notes"}:
        console.print("[red]Invalid field. Allowed: password, ntlm, aes128, aes256, ticket, cert, domain, notes[/]")
        return

    clean_value = None if value.strip() == "" else value
    updated = session.update_credential(session.current_target_label, cred["username"], **{field: clean_value})
    if updated:
        console.print(f"[green]✔ Updated {field}[/]")
    else:
        console.print(f"[yellow]No changes made to {field} (value was already set)[/]")

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
        console.print(f"[yellow]No credential found for user: {username}[/]")
        return

    if not force:
        confirm = typer.confirm(f"Delete credentials for '{username}'?")
        if not confirm:
            console.print("[yellow]Operation cancelled.[/]")
            return

    deleted = session.delete_credential(session.current_target_label, username)
    if deleted:
        if session.current_credential and session.current_credential.get("username") == username:
            console.print("[yellow]Deleted selected credential. No credential is now active.[/]")
        console.print(f"[green]✔ Deleted credentials for:[/] {username}")
    else:
        console.print("[red]✘ Failed to delete credential[/]")

@creds_app.command("fetch")
def fetch_creds():
    target = session.current_target
    cred = session.current_credential

    if not target:
        console.print("[red]No active target.[/]")
        return
    
    if not cred:
        console.print("[yellow]No credential selected. Use 'creds use' first.[/]")
        return

    username = cred.get("username")
    domain = cred.get("domain") or target.get("domain")
    password = cred.get("password")
    ntlm = cred.get("ntlm")
    aes128 = cred.get("aes128")
    aes256 = cred.get("aes256")
    ticket = cred.get("ticket")
    cert = cred.get("cert")

    if not username or not domain:
        console.print("[red]Missing username or domain.[/]")
        return

    # Fetch NTLM from password if missing
    if password and not ntlm:
        console.print("[blue]→ Deriving NTLM from password...[/]")
        derived_ntlm = utils.derive_ntlm(password)
        session.update_credential(session.current_target_label, username, ntlm=derived_ntlm)
        console.print(f"[green]✔ NTLM:[/] {derived_ntlm}")

    # Fetch AES keys if missing
    if password and not aes128:
        console.print("[blue]→ Deriving AES-128 from password...[/]")
        aes128 = utils.derive_aes(password, domain, username)
        session.update_credential(session.current_target_label, username, aes128=aes128)
        console.print(f"[green]✔ AES-128:[/] {aes128}")
    
    if password and not aes256:
        console.print("[blue]→ Deriving AES-256 from password...[/]")
        aes256 = utils.derive_aes(password, domain, username)
        session.update_credential(session.current_target_label, username, aes256=aes256)
        console.print(f"[green]✔ AES-256:[/] {aes256}")

    # Fetch Ticket if not present and we have any usable secret
    if not ticket:
        if password:
            console.print("[blue]→ Fetching ticket using password...[/]")
            success, result = utils.run_gettgt(domain, username, password=password, dc_ip=target.get("ip"))
        elif ntlm:
            console.print("[blue]→ Fetching ticket using NTLM hash...[/]")
            success, result = utils.run_gettgt(domain, username, ntlm=ntlm, dc_ip=target.get("ip"))
        elif aes128 or aes256:
            console.print("[blue]→ Fetching ticket using AES key...[/]")
            success, result = utils.run_gettgt(domain, username, aes128=aes128, aes256=aes256, dc_ip=target.get("ip"))
        elif cert:
            console.print("[blue]→ Fetching ticket using certificate...[/]")
            success, result = utils.run_cert_fetch(domain, username, cert, dc_ip=target.get("ip"))
        else:
            success, result = False, "No usable secret found to fetch ticket"

        if success:
            result_path = Path(result)
            cwd_path = Path.cwd() / result_path.name

            try:
                shutil.copy(result_path, cwd_path)
                session.update_credential(session.current_target_label, username, ticket=str(result_path))
                console.print(f"[green]✔ Ticket saved:[/] {result_path}")
                console.print(f"[green]✔ Credential updated with ticket path[/]")
                console.print(f"[green]✔ Ticket also copied to:[/] {cwd_path}")

                if result_path.exists():
                    os.environ["KRB5CCNAME"] = str(result_path)
                    console.print(f"[✔] KRB5CCNAME set to: {result_path}")
            except Exception as e:
                console.print(f"[red]✘ Failed to copy or update credential:[/] {e}")
        else:
            console.print(f"[red]Ticket fetch failed:[/] {result}")
    
    # Fetch cert if not present and we have any usable secret
    # Not implemented yet
 
app = creds_app