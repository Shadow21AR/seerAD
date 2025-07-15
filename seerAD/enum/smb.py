import subprocess
import os
from typing import List, Tuple, Dict
from rich.console import Console
from seerAD.core.session import session

console = Console()

def build_auth(method: str, cred: dict) -> Tuple[List[str], Dict[str, str]]:
    if method == "ticket":
        ticket = cred.get("ticket")
        if not ticket:
            raise ValueError("No Kerberos ticket present in credential.")
        return ["--use-kcache"], {"KRB5CCNAME": ticket}

    if method == "hash":
        if not cred.get("username") or not cred.get("ntlm"):
            raise ValueError("Need 'username' and 'ntlm' for hash auth.")
        return ["-u", cred["username"], "-H", cred["ntlm"]], {}

    if method == "password":
        if not cred.get("username") or not cred.get("password"):
            raise ValueError("Need 'username' and 'password' for password auth.")
        return ["-u", cred["username"], "-p", cred["password"]], {}

    if method == "anon":
        return ["-u", "''", "-p", "''"], {}

    raise ValueError(f"Unsupported auth method: {method}")

def run(method: str, extra_args: List[str]):
    if not session.current_target_label:
        console.print("[red]No active target set.[/]")
        return

    target = session.current_target
    cred = session.current_credential
    ip = target.get("ip")
    fqdn = target.get("fqdn") or target.get("hostname") or ip
    if not ip:
        console.print("[red]Target IP not set.[/]")
        return

    if not cred and method != "anon":
        console.print("[yellow]No credential selected. Use 'creds use' or use 'anon' mode.[/]")
        return

    try:
        target_host = fqdn if method == "ticket" else ip
        auth_args, env_vars = build_auth(method, cred or {})
        cmd = ["nxc", "smb", target_host] + auth_args + extra_args

        console.print(f"[dim]Running Command:[/] [yellow]{' '.join(cmd)}[/]")

        env = os.environ.copy()
        env.update(env_vars)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        console.print(result.stdout.strip() + "\n" + result.stderr.strip())

    except Exception as e:
        console.print(f"[red]SMB enum error: {e}[/]")
