import typer
from typing import List, Optional
from rich.console import Console
from seerAD.tool_handler.impacket_helper import run_impacket
from seerAD.tool_handler.nxc_helper import run_nxc
from seerAD.tool_handler.helper import run_command
from seerAD.core.session import session

console = Console()

COMMANDS = {
    # Impacket tools
    "adcomputers":      lambda m, a: run_impacket("GetADComputers", m, a),
    "adusers":          lambda m, a: run_impacket("GetADUsers", m, a),
    "npusers":          lambda m, a: run_impacket("GetNPUsers", m, a),
    "userspns":         lambda m, a: run_impacket("GetUserSPNs", m, a),
    "finddelegation":   lambda m, a: run_impacket("findDelegation", m, a),
    "lookupsid":        lambda m, a: run_impacket("lookupsid", m, a),
    "rpcdump":          lambda m, a: run_impacket("rpcdump", m, a),
    "samrdump":         lambda m, a: run_impacket("samrdump", m, a),
    "netview":          lambda m, a: run_impacket("netview", m, a),
    "gettgt":           lambda m, a: run_impacket("getTGT", m, a),

    # NXC tools
    "smb":              lambda m, a: run_nxc("smb", m, a),
    "ldap":             lambda m, a: run_nxc("ldap", m, a),
    "ssh":              lambda m, a: run_nxc("ssh", m, a),
    "mssql":            lambda m, a: run_nxc("mssql", m, a),
    "winrm":            lambda m, a: run_nxc("winrm", m, a),
    "wmi":              lambda m, a: run_nxc("wmi", m, a),
    "rdp":              lambda m, a: run_nxc("rdp", m, a),
    "vnc":              lambda m, a: run_nxc("vnc", m, a),
    "nfs":              lambda m, a: run_nxc("nfs", m, a),
    "ftp":              lambda m, a: run_nxc("ftp", m, a),
}

def list_modules():
    """List available enumeration modules"""
    console.print("[cyan bold]Available Enum Modules:[/]")
    cmds = ", ".join(sorted(COMMANDS.keys()))

    console.print(f"[green]{cmds}[/]")

def enum_callback(ctx: typer.Context):
    """Handle enum commands dynamically
    enum <command> <auth_method> [args...]"""
    if not ctx.args:
        list_modules()
        return
    module = ctx.args[0]
    method = ctx.args[1] if len(ctx.args) > 1 else "anon"
    extra_args = ctx.args[2:] if len(ctx.args) > 2 else []
    if module not in COMMANDS:
        console.print(f"[red][!] Unknown command: {module}[/]\n")
        console.print(list_modules())
        return
    # Ticket fallback logic
    if method == "anon" and session.current_credential.get("ticket") and len(ctx.args) == 1:
        method = "ticket"
    try:
        run_command(module, method, extra_args, COMMANDS)
    except Exception as e:
        console.print(f"[red][!] Error: {e}[/]")
        return