import subprocess
import os
import typer
from seerAD.core.session import session
from rich.console import Console

console = Console()
app = typer.Typer()


def build_auth(method: str, cred: dict) -> tuple[list[str], dict]:
    """Return (nxc args, env vars) based on selected auth method."""
    if method == "ticket":
        ticket = cred.get("ticket")
        if not ticket:
            raise ValueError("No Kerberos ticket present in credential.")
        return ["--use-kcache"], {"KRB5CCNAME": ticket}

    if method == "hash":
        if not cred.get("username") or not cred.get("ntlm"):
            raise ValueError("Credential must include 'username' and 'ntlm' for hash auth.")
        return ["-u", cred["username"], "-H", cred["ntlm"]], {}

    if method == "password":
        if not cred.get("username") or not cred.get("password"):
            raise ValueError("Credential must include 'username' and 'password' for password auth.")
        return ["-u", cred["username"], "-p", cred["password"]], {}

    if method == "anon":
        return ["-u", "''", "-p", "''"], {}


    raise ValueError(f"Unsupported method: {method}")


@app.command()
def run(method: str = typer.Argument(..., help="Auth method: ticket | hash | password | anon")):
    """
    Run SMB enum using selected auth method (positional).
    """
    if not session.current_target_label:
        console.print("[red]No active target.[/]")
        raise typer.Exit()

    target = session.current_target
    cred = session.current_credential
    ip = target.get("ip")
    fqdn = target.get("fqdn") or target.get("hostname") or ip

    if not ip:
        console.print("[red]No IP set for current target.[/]")
        return

    if not cred and method != "anon":
        console.print("[yellow]No credential selected. Use 'creds use' first or use 'anon'.[/]")
        return

    try:
        target_host = fqdn if method == "ticket" else ip
        auth_args, env_override = build_auth(method or "anon", cred or {})

        cmd = ["nxc", "smb", target_host] + auth_args + ["--shares"]

        console.print(f"[dim]Running Command: [/][bold yellow]{' '.join(cmd)}[/]")

        env = dict(os.environ)
        env.update(env_override)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        output = result.stdout + result.stderr
        console.print(output.strip())

    except FileNotFoundError:
        console.print("[red]Error: 'nxc' not found in PATH.[/]")
    except ValueError as ve:
        console.print(f"[red]{ve}[/]")
    except Exception as e:
        console.print(f"[red]Unhandled error: {e}[/]")