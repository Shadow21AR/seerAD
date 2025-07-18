
import os
import subprocess
from typing import List, Dict, Tuple
from rich.console import Console
from seerAD.core.session import session
from seerAD.tool_handler.helper import build_target_host, run_tool

console = Console()

def build_auth_args_nxc(method: str, cred: dict) -> Tuple[List[str], Dict[str, str]]:
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

    if method == "aes":
        if not cred.get("username") or not cred.get("aes256") or not cred.get("aes128"):
            raise ValueError("Username and AES hash required.")
        return ["-u", cred["username"], "--aesKey", cred["aes256"] or cred["aes128"]], {}

    if method == "anon":
        return ["-u", "''", "-p", "''"], {}

    raise ValueError(f"Unsupported auth method: {method}")

def get_ldap_args() -> List[str]:
    """Get LDAP specific command line arguments based on session data.
    
    Returns:
        List of command line arguments for LDAP operations
    """
    ldap_args = []
    if not hasattr(session, 'current_target'):
        return ldap_args
        
    # Add domain if available in session
    if session.current_target.get('domain'):
        ldap_args.extend(["-d", session.current_target['domain']])
    
    # Add DNS server if available in session
    if session.current_target.get('ip'):
        ldap_args.extend(["--dns-server", session.current_target['ip']])
    
    return ldap_args

def run_nxc(tool: str, method: str, extra_args: List[str]):
    if not session.current_target_label:
        console.print("[red]No target set.[/]")
        return

    if method != "anon" and not session.current_credential:
        console.print("[yellow]No credential selected. Use 'creds use' or use 'anon'.[/]")
        return

    try:
        target = build_target_host(method)
        auth_args, env_vars = build_auth_args_nxc(method, session.current_credential or {})
        more_args = get_ldap_args() if tool.lower() == "ldap" else []
        
        cmd = ["nxc", tool, target] + auth_args + more_args + extra_args

        env = os.environ.copy()
        env.update(env_vars)

        run_tool(cmd, env=env)

    except Exception as e:
        console.print(f"[red]{tool.upper()} error: {e}[/]")