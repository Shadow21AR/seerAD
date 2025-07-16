# seerAD/enum/utils.py

import os
import subprocess
from typing import List, Dict, Tuple
from rich.console import Console
from seerAD.core.session import session

console = Console()

def build_auth_args(method: str, cred: dict) -> Tuple[List[str], Dict[str, str]]:
    if method == "ticket":
        ticket = cred.get("ticket")
        if not ticket:
            raise ValueError("No Kerberos ticket found.")
        return ["--use-kcache"], {"KRB5CCNAME": ticket}

    if method == "password":
        if not cred.get("username") or not cred.get("password"):
            raise ValueError("Username and password required.")
        return ["-u", cred["username"], "-p", cred["password"]], {}

    if method == "hash":
        if not cred.get("username") or not cred.get("ntlm"):
            raise ValueError("Username and NTLM hash required.")
        return ["-u", cred["username"], "-H", cred["ntlm"]], {}

    if method == "anon":
        return ["-u", "''", "-p", "''"], {}

    raise ValueError(f"Unsupported auth method: {method}")


def build_target_host(method: str) -> str:
    target = session.current_target
    ip = target.get("ip")
    fqdn = target.get("fqdn") or target.get("hostname") or ip
    return fqdn if method == "ticket" else ip


def run_nxc(tool: str, method: str, extra_args: List[str]):
    if not session.current_target_label:
        console.print("[red]No target set.[/]")
        return

    if method != "anon" and not session.current_credential:
        console.print("[yellow]No credential selected. Use 'creds use' or use 'anon'.[/]")
        return

    try:
        target = build_target_host(method)
        auth_args, env_vars = build_auth_args(method, session.current_credential or {})
        cmd = ["nxc", tool, target] + auth_args + extra_args

        console.print(f"[dim]Running Command:[/] [yellow]{' '.join(cmd)}[/]")
        env = os.environ.copy()
        env.update(env_vars)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        console.print(result.stdout.strip() + "\n" + result.stderr.strip())

    except Exception as e:
        console.print(f"[red]{tool.upper()} enum error: {e}[/]")