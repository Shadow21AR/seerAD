from typing import List, Dict, Callable
from rich.console import Console
from seerAD.core.session import session
import subprocess

console = Console()

def run_tool(cmd: List[str], env: Dict[str, str] = None) -> None:
    console.print(f"[red]❯[/] [yellow]{' '.join(cmd)}[/]")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)

    for line in process.stdout:
        console.print(line.rstrip())

    process.wait()
    if process.returncode != 0:
        console.print(f"[red][!] Process exited with code {process.returncode}[/]")

def run_command(command: str, method: str, args: List[str], COMMANDS: Dict[str, Callable]) -> None:
    creds = session.current_credential
    if not creds.get(method):
        console.print(f"[yellow]You dont have {method} in your selected credentials. Check availbale auth method via 'creds info'[/]")
        return
    handler = COMMANDS.get(command.lower())
    if not handler:
        console.print(f"[red][!] Unknown command: {command}[/]")
        return
    handler(method, args)

def build_target_host(method: str) -> str:
    target = session.current_target
    ip = target.get("ip")
    fqdn = target.get("fqdn") or target.get("hostname") or ip
    return fqdn if method == "ticket" or "aes" else ip

def default_target_format(method: str, target: dict) -> str:
    return target["fqdn"] if method == "ticket" or "aes" else target["ip"]

def resolve_flags(flags: List[str], cred: dict, target: dict) -> List[str]:
    resolved = []
    combined = target.copy()
    combined.update(cred)

    for f in flags:
        if "<ntlm>" in f:
            f = f.replace("<ntlm>", cred.get("ntlm", ""))
        if "<aes>" in f:
            f = f.replace("<aes>", cred.get("aes256", "") or cred.get("aes128", ""))
        resolved.append(f.format(**combined))
    return resolved

def impacket_identity(method: str, target: dict, cred: dict) -> str:
    if method == "password":
        return f"{target['domain']}/{cred['username']}:{cred['password']}"
    elif method in ("ticket", "hash", "aes"):
        return f"{target['domain']}/{cred['username']}"
    elif method == "anon":
        raise ValueError("Anonymous auth is not supported for this tool.")
    else:
        raise ValueError(f"Unsupported auth method: {method}")
