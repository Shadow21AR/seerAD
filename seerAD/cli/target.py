import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
from ipaddress import ip_address, AddressValueError

from seerAD.core.session import session

console = Console()
target_app = typer.Typer(help="Target commands")

ALLOWED_ATTRS = ['ip', 'domain', 'fqdn']

def validate_ip(ip: str) -> bool:
    try:
        ip_address(ip)
        return True
    except AddressValueError:
        return False

def print_target_table(targets: dict, current_label: str = None) -> None:
    if not targets:
        console.print("[yellow]No targets found.[/]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    for col in ["Label", "IP", "Domain", "FQDN"]:
        table.add_column(col, style="cyan")

    for label, target in targets.items():
        t = target.to_dict() if hasattr(target, "to_dict") else target
        is_current = label == current_label
        row = [
            f"[bold green]{label}*[/]" if is_current else label,
            f"[bold green]{t.get('ip') or '-'}[/]" if is_current else t.get('ip') or "-",
            f"[bold green]{t.get('domain') or '-'}[/]" if is_current else t.get('domain') or "-",
            f"[bold green]{t.get('fqdn') or '-'}[/]" if is_current else t.get('fqdn') or "-",
        ]
        table.add_row(*row)

    console.print(table)

@target_app.command("list")
def target_list():
    """List all targets."""
    print_target_table(session.targets, session.current_target_label)

@target_app.command("switch")
def target_switch(label: str = typer.Argument(..., help="Label of the target to switch to")):
    """Switch to a different target."""
    if session.switch_target(label):
        console.print(f"[green]✔ Switched to target:[/] {label}")
    else:
        console.print(f"[red]✘ Target not found:[/] {label}")
        return

@target_app.command("add")
def target_add(
    label: str = typer.Argument(..., help="Label of the target"),
    ip: str = typer.Argument(..., help="IP address"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d"),
    fqdn: Optional[str] = typer.Option(None, "--fqdn", "-f"),
):
    """Add a new target."""
    if not validate_ip(ip):
        console.print(f"[red]✘ Invalid IP address:[/] {ip}")
        return

    success = session.add_target(
        label, ip, domain=domain, fqdn=fqdn
    )
    if not success:
        console.print(f"[red]✘ Target '{label}' already exists[/]")
        return

    console.print(f"[green]✔ Added target:[/] {label} ({ip})")

    if not session.current_target_label:
        session.switch_target(label)
        console.print(f"[yellow]Updated '{label}' as current target[/]")

@target_app.command("set")
def target_set(
    key: str = typer.Argument(..., help="Attribute to set (ip, domain, fqdn)"),
    value: str = typer.Argument(..., help="New value (use '' to clear the field)"),
):
    """Update an attribute of the current target."""
    if not session.current_target_label:
        console.print("[red]✘ No active target. Use 'target switch <label>' first.[/]")
        return

    if key not in ALLOWED_ATTRS:
        console.print(f"[red]✘ Invalid attribute. Allowed: {', '.join(ALLOWED_ATTRS)}[/]")
        return

    value = value.strip() or None
    if key == 'ip' and value and not validate_ip(value):
        console.print(f"[red]✘ Invalid IP address:[/] {value}")
        return

    if session.update_current_target(**{key: value}):
        console.print(f"[green]✔ Updated '{key}' for target '{session.current_target_label}'[/]")
    else:
        console.print("[red]✘ Failed to update target[/]")
        return

@target_app.command("info")
def target_info():
    """Show detailed info about the current target."""
    if not session.current_target_label:
        console.print("[yellow]No target selected. Use 'target switch <label>'[/]")
        return

    target = session.current_target
    if not target:
        console.print("[red]✘ Current target not found.[/]")
        return

    table = Table(show_header=False)
    table.add_row("[bold cyan]Label[/]", session.current_target_label)
    table.add_row("[bold cyan]IP[/]", target.get('ip', '-'))
    table.add_row("[bold cyan]Domain[/]", target.get('domain', '-'))
    table.add_row("[bold cyan]FQDN[/]", target.get('fqdn', '-'))
    console.print(table)

    creds = session.get_credentials()
    console.print(f"\n[bold]Credentials:[/] {len(creds)} found")

    if creds:
        creds_table = Table(show_header=True, header_style="bold")
        creds_table.add_column("Username")
        creds_table.add_column("Password / Hash")
        for cred in creds:
            creds_table.add_row(
                cred.get("username", "-"),
                cred.get("password", "-") or "-"
            )
        console.print(creds_table)

@target_app.command("del")
def target_del(label: str = typer.Argument(..., help="Label of the target to delete")):
    """Delete a target by label."""
    if label == session.current_target_label:
        console.print("[yellow]✘ Cannot delete the currently selected target.[/]")
        return

    if session.delete_target(label):
        console.print(f"[green]✔ Deleted target:[/] {label}")
    else:
        console.print(f"[red]✘ Target not found:[/] {label}")
        return

# Attach to main app
app = target_app