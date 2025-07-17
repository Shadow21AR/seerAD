from typing import Dict, Callable, List
from .utils import run_impacket, run_nxc
from seerAD.core.session import session
from seerAD.cli.main import console

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

def run_command(command: str, method: str, args: List[str]) -> None:
    handler = COMMANDS.get(command.lower())
    if not handler:
        console.print(f"[red][!] Unknown command: {command}[/]")
        return
    handler(method, args)

def list_commands() -> Dict[str, Callable]:
    return COMMANDS.copy()
