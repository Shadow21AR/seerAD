# seerAD/enum/utils.py

import os
import subprocess
from typing import List, Dict, Tuple
from rich.console import Console
from seerAD.core.session import session

console = Console()

# =============================
# NXClient Helpers
# =============================

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
        auth_args, env_vars = build_auth_args_nxc(method, session.current_credential or {})
        cmd = ["nxc", tool, target] + auth_args + extra_args

        console.print(f"[dim]Running Command:[/] [yellow]{' '.join(cmd)}[/]")
        env = os.environ.copy()
        env.update(env_vars)

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        console.print(result.stdout.strip() + "\n" + result.stderr.strip())

    except Exception as e:
        console.print(f"[red]{tool.upper()} enum error: {e}[/]")

# =============================
# Impacket Helpers
# =============================

def default_target_format(method: str, target: dict) -> str:
    return target["fqdn"] if method == "ticket" else target["ip"]

def resolve_flags(flags: List[str], cred: dict, target: dict) -> List[str]:
    resolved = []
    combined = target.copy()
    combined.update(cred)

    for f in flags:
        f = f.replace("<ntlm>", cred.get("ntlm", ""))
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

IMPACKET_TOOL_CONFIG = {
    "getnpusers": {
        "target": impacket_identity,
        "auth": {
            "ticket": ["-k", "-no-pass"],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"],
            "password": []
        },
        "extra": ["-dc-ip", "{ip}", "-dc-host", "{fqdn}"],
    },
    "getuserspns": {
        "target": impacket_identity,
        "auth": {
            "ticket": ["-k", "-no-pass"],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"],
            "password": []
        },
        "extra": ["-dc-ip", "{ip}", "-dc-host", "{fqdn}"],
    },
    "getadcomputers": {
        "target": impacket_identity,
        "auth": {
            "ticket": ["-k", "-no-pass"],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"],
            "password": []
        },
        "extra": ["-dc-ip", "{ip}", "-dc-host", "{fqdn}"],
    },
    "getadusers": {
        "target": impacket_identity,
        "auth": {
            "ticket": ["-k", "-no-pass"],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"],
            "password": []
        },
        "extra": ["-dc-ip", "{ip}", "-dc-host", "{fqdn}"],
    },
    "finddelegation": {
        "target": impacket_identity,
        "auth": {
            "ticket": ["-k", "-no-pass"],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"],
            "password": []
        },
        "extra": ["-dc-ip", "{ip}", "-dc-host", "{fqdn}"],
    },
    "gettgt": {
        "target": impacket_identity,
        "auth": {
            "password": [],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"]
        },
        "extra": ["-dc-ip", "{ip}"],
    },
    "lookupsid": {
        "target": lambda m, t, c: (
            f"{t['domain']}/{c['username']}:{c['password']}@{t['ip']}" if m == "password" else
            f"{t['domain']}/{c['username']}@{t['ip']}" if m in ("hash", "ticket") else
            (_ for _ in ()).throw(ValueError("lookupsid only supports password, hash, or ticket authentication"))
        ),
        "auth": {
            "password": [],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "ticket": ["-k", "-no-pass"]
        },
        "extra": ["-target-ip", "{ip}"],
    },
    "rpcdump": {
        "target": lambda m, t, c: (
            f"{t['domain']}/{c['username']}@{t['ip']}"
            if m == "hash" else (_ for _ in ()).throw(ValueError("rpcdump only supports hash authentication"))
        ),
        "auth": {"hash": ["-hashes", ":<ntlm>"]},
        "extra": ["-target-ip", "{ip}"],
    },
    "samrdump": {
        "target": lambda m, t, c: (
            f"{t['domain']}/{c['username']}:{c['password']}@{t['ip']}" if m == "password" else
            f"{t['domain']}/{c['username']}@{t['ip']}" if m in ("hash", "ticket", "aes") else
            (_ for _ in ()).throw(ValueError("samrdump only supports password, hash, ticket, or aes authentication"))
        ),
        "auth": {
            "password": [],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "ticket": ["-k", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"]
        },
        "extra": ["-target-ip", "{ip}"],
    },
    "netview": {
        "target": lambda m, t, c: (
            f"{t['domain']}/{c['username']}:{c['password']}" if m == "password" else
            f"{t['domain']}/{c['username']}" if m in ("hash", "ticket", "aes") else
            (_ for _ in ()).throw(ValueError("netview only supports password, hash, ticket, or aes authentication"))
        ),
        "auth": {
            "password": [],
            "hash": ["-hashes", ":<ntlm>", "-no-pass"],
            "ticket": ["-k", "-no-pass"],
            "aes": ["-aesKey", "<aes>", "-no-pass"]
        },
        "extra": ["-dc-ip", "{ip}"],
    },
    "getarch": {
        "target": lambda m, t, c: (_ for _ in ()).throw(
            ValueError("getArch does not support authentication")
        ) if m != "anon" else "",
        "auth": {"anon": []},
        "extra": ["-target", "{ip}"],
    },
}

def run_impacket(tool: str, method: str, extra_args: List[str]):
    if not session.current_target_label:
        console.print("[red]No target set.[/]")
        return

    if method != "anon" and not session.current_credential:
        console.print("[yellow]No credential selected. Use 'creds use' or use 'anon'.[/]")
        return

    try:
        target = session.current_target
        cred = session.current_credential or {}

        config = IMPACKET_TOOL_CONFIG.get(tool.lower())
        if not config:
            console.print(f"[red]No config for tool: {tool}[/]")
            return

        target_str = config["target"](method, target, cred)
        auth_flags = resolve_flags(config.get("auth", {}).get(method, []), cred, target)
        extra_flags = resolve_flags(config.get("extra", []), cred, target)

        args = [target_str] + auth_flags + extra_flags + extra_args
        cmd = [f"{tool}.py"] + args

        env = os.environ.copy()
        if method == "ticket" and cred.get("ticket"):
            env["KRB5CCNAME"] = cred["ticket"]
        env["PYTHONWARNINGS"] = "ignore::UserWarning"

        console.print(f"[dim]Running Command:[/] [yellow]{' '.join(cmd)}[/]")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        console.print(result.stdout.strip() + "\n" + result.stderr.strip())

    except Exception as e:
        console.print(f"[red]{tool} error: {e}[/]")
