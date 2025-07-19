
import os
import subprocess
import shutil
from typing import List, Dict, Tuple
from rich.console import Console
from seerAD.core.session import session
from seerAD.tool_handler.helper import build_target_host_bloodyAD, run_tool

console = Console()

def build_auth_args_bloodyad(method: str, cred: dict) -> Tuple[List[str], Dict[str, str]]:
    if method == "ticket":
        ticket = cred.get("ticket")
        if not ticket:
            raise ValueError("No Kerberos ticket found.")
        return ["-k"], {"KRB5CCNAME": ticket}

    if method == "password":
        if not cred.get("username") or not cred.get("password"):
            raise ValueError("Username and password required.")
        return ["-u", cred["username"], "-p", cred["password"]], {}

    if method == "ntlm":
        if not cred.get("username") or not cred.get("ntlm"):
            raise ValueError("Username and NTLM hash required.")
        return ["-u", cred["username"], "-p", cred["ntlm"]], {}

    if method == "aes128":
        if not cred.get("username") or not cred.get("aes128"):
            raise ValueError("Username and AES key (128) required.")
        return ["-u", cred["username"], "-p", cred["aes128"], "-f", "aes", "-k"], {}

    if method == "aes256":
        if not cred.get("username") or not cred.get("aes256"):
            raise ValueError("Username and AES key (256) required.")
        return ["-u", cred["username"], "-p", cred["aes256"], "-f", "aes", "-k"], {}

    if method == "anon":
        raise ValueError("bloodyAD does not support anonymous authentication.")

    raise ValueError(f"Unsupported auth method for bloodyAD: {method}")


def run_bloodyad(tool: List[str], method: str, args: List[str]):
    if shutil.which("bloodyAD") is None:
        console.print("[red]bloodyAD not found. Please install bloodyAD.[/]")
        console.print("[yellow]You can install bloodyAD using 'pipx install bloodyAD'.[/]")
        return
    
    if not session.current_target_label:
        console.print("[red]No target set.[/]")
        return
    
    if method != "anon" and not session.current_credential:
        console.print("[yellow]No credential selected. Use 'creds use' or use 'anon'.[/]")
        return
    
    try:
        target = build_target_host_bloodyAD(method)
        auth_args, env_vars = build_auth_args_bloodyad(method, session.current_credential or {})
        cmd = ["bloodyAD"] + target + auth_args + tool + args
        env = os.environ.copy()
        env.update(env_vars)
        run_tool(cmd, env=env)
    except Exception as e:
        console.print(f"[red]{tool[0].upper() + tool[1:]} error: {e}[/]")