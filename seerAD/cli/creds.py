import typer
from typing import Optional
from rich.console import Console
from rich.table import Table, box
from seerAD.core.session import session
from seerAD.core.creds import AuthType

console = Console()
creds_app = typer.Typer(help="Credentials commands")


def get_credential_property(cred: dict, prop: str, default=None):
    return cred.get(prop, default)


@creds_app.command("add")
def creds_add(
    username: str = typer.Argument(..., help="Username to add"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain for the credentials"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
    ntlm: Optional[str] = typer.Option(None, "--ntlm", "-n", help="NTLM hash"),
    aes: Optional[str] = typer.Option(None, "--aes", help="AES key"),
    ticket: Optional[str] = typer.Option(None, "--ticket", help="Kerberos ticket (path or blob)"),
    cert: Optional[str] = typer.Option(None, "--cert", help="Certificate file or content"),
    token: Optional[str] = typer.Option(None, "--token", help="token"),
    notes: Optional[str] = typer.Option("", "--notes", "-N", help="Additional notes"),
):
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    creds = session.get_credentials(session.current_target_label)

    newCred = {
        "username": username,
        "password": password or "",
        "ntlm": ntlm or "",
        "aes": aes or "",
        "ticket": ticket or "",
        "cert": cert or "",
        "token": token or "",
        "domain": domain or "",
        "notes": notes or "",
    }

    if any(c.get("username") == username for c in creds):
        console.print(f"[yellow]✘ Credential for user '{username}' already exists.[/]")
        return

    session.add_credential(session.current_target_label, newCred)

@creds_app.command("list")
def creds_list():
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    all_creds = session.get_credentials(session.current_target_label)

    display_types = ["password", "ntlm", "aes", "ticket", "cert", "token"]

    table = Table(title=f"Credentials for {session.current_target_label}", box=box.ROUNDED)
    table.add_column("Username", style="cyan", no_wrap=True)
    for a in display_types:
        table.add_column(a.replace('_', ' ').title(), justify="center")

    current_cred = session.current_credential
    current_uname = get_credential_property(current_cred, "username") if current_cred else None

    seen_usernames = set()

    for cred in all_creds:
        uname = get_credential_property(cred, "username") or "<unknown>"
        seen_usernames.add(uname)

        row = [f"[bold green]{uname}[/]" if uname == current_uname else uname]
        for field in display_types:
            val = get_credential_property(cred, field)
            row.append("✔" if val else "✘")
        table.add_row(*row)

    # In case current_cred user exists but no full cred entry exists
    if current_uname and current_uname not in seen_usernames:
        row = [f"[bold green]{current_uname}[/]"]
        row += ["✘"] * len(display_types)
        table.add_row(*row)

    console.print(table)


@creds_app.command("show")
def creds_show():
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    cred = session.current_credential
    if not cred:
        console.print("[yellow]No credential selected. Use 'creds use' to set one.[/]")
        return

    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Field", style="cyan", width=15)
    table.add_column("Value", style="green")

    table.add_row("Username", get_credential_property(cred, "username"))
    table.add_row("Target", session.current_target_label)
    table.add_section()

    auth_type = get_credential_property(cred, 'auth_type') or ""
    secret = get_credential_property(cred, 'secret', '')

    display = str(secret) if secret else ""
    if auth_type == "FILE":
        display = f"[dim]{secret}[/]"

    table.add_row(auth_type.replace('_', ' ').title(), display)

    domain = get_credential_property(cred, 'domain')
    if domain:
        table.add_row("Domain", domain)

    notes = get_credential_property(cred, 'notes')
    if notes:
        table.add_row("Notes", notes)

    console.print(f"\n[bold]Current credential: [cyan]{get_credential_property(cred, 'username')}[/] on [cyan]{session.current_target_label}[/][/]")
    console.print(table)


@creds_app.command("use")
def creds_use(
    username: str = typer.Argument(..., help="Username to set as current credential"),
    auth_type: Optional[str] = typer.Option(None, "--auth-type", "-t", help="Specify auth type to match (e.g., password, ntlm_hash, etc.)")
):
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    creds_list = session.get_credentials(session.current_target_label, username=username, auth_type=auth_type)
    if not creds_list:
        console.print("[red]No matching credential found.[/]")
        return

    # Use first matching credential's index
    cred = creds_list[0]
    all_creds = session.get_credentials(session.current_target_label)
    index = all_creds.index(cred)
    if session.use_credential(index):
        console.print(f"[green]✔ Selected credential:[/] {username} ({cred.get('auth_type')})")
    else:
        console.print("[red]Failed to select credential.[/]")


@creds_app.command("set")
def creds_set(
    field: str = typer.Argument(..., help="Field to update (e.g., password, ntlm_hash, token, file, domain, notes)"),
    value: str = typer.Argument(..., help="Value to set (use '' to clear)"),
):
    if not session.current_target_label:
        console.print("[red]No active target. Use 'target switch' first.[/]")
        return

    cred = session.current_credential()
    if not cred:
        console.print("[red]No current credential selected. Use 'creds use' first.[/]")
        return

    allowed_fields = {
        "password": "PASSWORD",
        "ntlm_hash": "NTLM_HASH",
        "aes_key": "AES_KEY",
        "ticket": "TICKET",
        "certificate": "CERTIFICATE",
        "domain": "domain",
        "notes": "notes",
    }

    if field not in allowed_fields:
        console.print(f"[red]Invalid field: {field}[/]")
        console.print(f"[yellow]Valid fields:[/] {', '.join(allowed_fields.keys())}")
        return

    username = cred.get("username")

    if value == "":
        value = None

    is_auth_field = field in ["password", "ntlm_hash", "aes_key", "ticket", "certificate"]
    if is_auth_field:
        updated = session.add_credential(
            session.current_target_label,
            {
                "username": username,
                "auth_type": allowed_fields[field],
                "secret": value or "",
                "domain": cred.get("domain", ""),
                "notes": cred.get("notes", ""),
            }
        )
    else:
        # domain or notes
        updated = session.add_credential(
            session.current_target_label,
            {
                "username": username,
                "auth_type": cred.get("auth_type", ""),
                "secret": cred.get("secret", ""),
                "domain": value if field == "domain" else cred.get("domain", ""),
                "notes": value if field == "notes" else cred.get("notes", ""),
            }
        )

    if updated:
        console.print(f"[green]✔ Updated {field} for:[/] {username}")
    else:
        console.print(f"[red]Failed to update {field}[/]")


@creds_app.command("del")
def creds_del(
    username: str = typer.Argument(..., help="Username to delete"),
    auth_type: Optional[str] = typer.Option(None, "--auth-type", "-t", help="Delete specific auth type only"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
):
    if not session.current_target_label:
        console.print("[red]No active target. Use 'init' or 'target switch' first.[/]")
        return

    creds_list = session.get_credentials(session.current_target_label, username=username, auth_type=auth_type)
    if not creds_list:
        console.print("[yellow]No matching credentials found.[/]")
        return

    if not force:
        confirm = typer.confirm(f"Delete {len(creds_list)} credential(s) for {username}{f' ({auth_type})' if auth_type else ''}?")
        if not confirm:
            console.print("[yellow]Cancelled.[/]")
            return

    deleted_count = 0
    for cred in creds_list:
        if session.delete_credential(session.current_target_label, username, cred.get("auth_type")):
            deleted_count += 1

    if deleted_count:
        console.print(f"[green]✔ Deleted {deleted_count} credential(s) for:[/] {username}")
        # Clear current credential if it matches deleted user
        current_cred = session.current_credential()
        if current_cred and current_cred.get("username") == username:
            session.current_credential_index = None
            console.print("[yellow]Current credential cleared.[/]")
    else:
        console.print("[red]No credentials deleted.[/]")

app = creds_app