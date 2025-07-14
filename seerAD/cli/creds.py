import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table, box
from seerAD.core.session import session

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
            "✔"  if cred.get("aes") else "✘",
            "✔" if cred.get("ticket") else "✘",
            "✔" if cred.get("cert") else "✘",
            "✔" * 8 if cred.get("token") else "✘",
            (str(cred.get("notes") or "")[:20] + "...") if len(str(cred.get("notes") or "")) > 20 else str(cred.get("notes") or "")
        )

    console.print(table)

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

@creds_app.command("show")
def creds_show():
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

app = creds_app