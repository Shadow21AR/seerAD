
import os
import shutil
from typing import List, Dict, Tuple, Any
from rich.console import Console
from seerAD.core.session import session
from seerAD.tool_handler.helper import build_target_host_certipy, run_tool

console = Console()

def build_auth_args_certipy(method: str, cred: Dict[str, Any]) -> Tuple[List[str], Dict[str, str]]:
    args = []
    env = {}

    user = cred.get("username", "")
    domain = cred.get("domain", "") or session.current_target.get("domain", "")
    upn = f"{user}@{domain}" if user and domain else ""
    args += ["-u", upn]

    if method == "password":
        if not cred.get("password"):
            raise ValueError("Password required.")
        args += ["-p", cred["password"]]

    elif method == "ntlm":
        if not cred.get("ntlm"):
            raise ValueError("NTLM hash required.")
        args += ["-hashes", f":{cred['ntlm']}"]

    elif method == "aes128":
        if not cred.get("aes128"):
            raise ValueError("AES key (128) required.")
        args += ["-aes", cred["aes128"]]

    elif method == "aes256":
        if not cred.get("aes256"):
            raise ValueError("AES key (256) required.")
        args += ["-aes", cred["aes256"]]

    elif method == "ticket":
        if not cred.get("ticket"):
            raise ValueError("Kerberos ticket required.")
        args += ["-k"]
        env["KRB5CCNAME"] = cred["ticket"]

    elif method == "cert":
        if not cred.get("cert") or not cred.get("key"):
            raise ValueError("Certificate and key required.")
        args += ["-key", cred["key"], "-cert", cred["cert"]]

    return args, env

def run_certipy(tool: List[str], method: str, args: List[str]):
    if shutil.which("certipy-ad") is None:
        console.print("[red]certipy-ad not found. Please install certipy-ad.[/]")
        console.print("[yellow]You can install certipy-ad using 'pipx install certipy-ad'.[/]")
        return
    
    if not session.current_target_label:
        console.print("[red]No target set.[/]")
        return
    
    if not session.current_credential:
        console.print("[yellow]No credential selected. Use 'creds use'.[/]")
        return
    
    try:
        target = build_target_host_certipy(method)
        auth_args, env_vars = build_auth_args_certipy(method, session.current_credential or {})
        global_args = ["-debug"]
        cmd = ["certipy-ad"] + [arg for arg in global_args if any(x == arg for x in args)] + [tool] + auth_args + target + [arg for arg in args if arg not in global_args]
        env = os.environ.copy()
        env.update(env_vars)
        run_tool(cmd, env=env)
    except Exception as e:
        console.print(f"[red]{tool[0].upper() + tool[1:]} error: {e}[/]")