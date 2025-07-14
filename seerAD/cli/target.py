import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
from ipaddress import ip_address, AddressValueError

from seerAD.core.session import session

console = Console()
target_app = typer.Typer(help="Target commands")

ALLOWED_ATTRS = ['ip', 'hostname', 'domain', 'fqdn', 'os']

def validate_ip(ip: str) -> bool:
    try:
        ip_address(ip)
        return True
    except AddressValueError:
        return False

@target_app.command("add")
def target_add(label: str = typer.Argument(..., help="Label of the target to add"),
    ip: str = typer.Argument(..., help="IP address of the target"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain name"),
    hostname: Optional[str] = typer.Option(None, "--hostname", "-h", help="Hostname"),
    fqdn: Optional[str] = typer.Option(None, "--fqdn", "-f", help="Fully qualified domain name"),
    os: Optional[str] = typer.Option(None, "--os", "-o", help="Operating system"),
) -> None:
    """Add a new target."""
    targets = session.list_targets()
    for t_label, t_target in targets.items():
        if label == t_label:
            console.print(f"[red]✘ Target '{label}' already exists.[/]")
            return
    
    if not session.validate_ip(ip):
        console.print("[red]✘ Invalid IP address format. Use IPv4 (e.g., 192.168.1.1)[/]")
        return

    session.add_target(label, {
        "ip": ip,
        "domain": domain or "",
        "hostname": hostname or "",
        "fqdn": fqdn or "",
        "os": os or "Unknown",
    })

    console.print(f"[green]✔ Target added:[/] {label}")

@target_app.command("list")
def target_list() -> None:
    """List all targets."""
    targets = session.list_targets()
    if not targets:
        console.print("[yellow]No targets found[/]")
        return

    table = Table(title="Targets")
    table.add_column("Label", style="cyan")
    table.add_column("IP")
    table.add_column("Hostname")
    table.add_column("Domain")
    table.add_column("FQDN")
    table.add_column("OS")

    current_label = session.current_target_label

    for label, target in targets.items():
        is_current = (label == current_label)
        label_display = f"[bold green]{label}[/] [bold green](current)[/]" if is_current else label
        table.add_row(
            label_display,
            target.get("ip") or "-",
            target.get("hostname") or "-",
            target.get("domain") or "-",
            target.get("fqdn") or "-",
            target.get("os") or "-",
        )

    console.print(table)

@target_app.command("switch")
def target_switch(label: str = typer.Argument(..., help="Label of the target to switch to")) -> None:
    """Switch to another target."""
    if session.switch_target(label):
        console.print(f"[green]✔ Switched to target:[/] {label}")
    else:
        console.print(f"[red]✘ Target not found:[/] {label}")

@target_app.command("set")
def target_set(
    key: str = typer.Argument(..., help="Attribute to set (ip, hostname, domain, fqdn, os)"),
    value: str = typer.Argument(..., help="Value to set (use '' to clear the field)"),
) -> None:
    """Set target attribute."""

    if not session.current_target_label:
        console.print("[red]✘ No active target. Use 'init' or 'target switch' first.[/]")
        return

    key = key.lower()
    if key not in ALLOWED_ATTRS:
        console.print(f"[red]✘ Invalid attribute: {key}[/]")
        console.print(f"Valid attributes: {', '.join(ALLOWED_ATTRS)}")
        return

    value = value.strip() or None

    if key == "ip" and value and not validate_ip(value):
        console.print("[red]✘ Invalid IP address format. Use IPv4 (e.g., 192.168.1.1)[/]")
        return

    target = session.targets.get(session.current_target_label, {})
    if target.get(key) == value:
        console.print(f"[yellow]⚠ {key} already set to this value[/]")
        return

    # Update target and save session
    target[key] = value
    session.targets[session.current_target_label] = target
    session.save_session()

    console.print(f"[green]✔ Updated {key}:[/] {value or '(cleared)'}")
    target_info()

@target_app.command("info")
def target_info() -> None:
    """Show current target information."""
    if not session.current_target_label:
        console.print("[yellow]No active target. Use 'init' or 'target switch' first.[/]")
        return

    target = session.targets.get(session.current_target_label, {})
    label = session.current_target_label

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", min_width=12)
    table.add_column("Value", style="white")

    table.add_row("Label", label)
    table.add_row("IP", target.get("ip") or "-")
    table.add_row("Hostname", target.get("hostname") or "-")
    table.add_row("Domain", target.get("domain") or "-")
    table.add_row("FQDN", target.get("fqdn") or "-")
    table.add_row("OS", target.get("os") or "-")

    from datetime import datetime
    created_at = target.get("created_at")
    updated_at = target.get("updated_at")

    if created_at:
        created_fmt = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
        table.add_row("", "")
        table.add_row("Created", f"[dim]{created_fmt}")

    if updated_at and updated_at != created_at:
        updated_fmt = datetime.fromisoformat(updated_at).strftime('%Y-%m-%d %H:%M:%S')
        table.add_row("Updated", f"[dim]{updated_fmt}")

    console.print("\n[bold cyan]Target Information[/]")
    console.print(table)

@target_app.command("init")
def target_init(
    label: str = typer.Argument(..., help="Label for the target (used as directory)"),
    ip: str = typer.Argument(..., help="IP address of the target"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain name"),
    hostname: Optional[str] = typer.Option(None, "--hostname", "-h", help="Hostname"),
    fqdn: Optional[str] = typer.Option(None, "--fqdn", "-f", help="Fully qualified domain name"),
) -> None:
    """Initialize a new target session."""

    if not validate_ip(ip):
        console.print("[red]✘ Invalid IP address format. Use IPv4 (e.g., 192.168.1.1)[/]")
        return

    if label in session.targets:
        console.print(f"[red]✘ Target '{label}' already exists.[/]")
        return

    from datetime import datetime
    now = datetime.utcnow().isoformat()

    target_data = {
        "ip": ip,
        "domain": domain or "",
        "hostname": hostname or "",
        "fqdn": fqdn or "",
        "os": "Unknown",
        "created_at": now,
        "updated_at": now,
    }

    session.add_target(label, target_data)

    if session.switch_target(label):
        console.print(f"[green]✔ Target created and set as current:[/] {label}")
    else:
        console.print(f"[yellow]⚠ Target created but failed to set as current:[/] {label}")

    target_info()

@target_app.command("del")
def target_del(label: str = typer.Argument(..., help="Label of the target to delete")) -> None:
    """Delete a target."""
    if session.current_target_label == label:
        console.print("[yellow]Cannot delete the current target. Switch to another target first.[/]")
        return

    if session.delete_target(label):
        console.print(f"[green]✔ Deleted target:[/] {label}")
        if not session.list_targets():
            console.print("[yellow]No targets left. Use 'target add' to create a new one.[/]")
    else:
        console.print(f"[red]✘ Target not found:[/] {label}")

app = target_app
