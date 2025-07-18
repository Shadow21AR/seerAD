import os
import subprocess
from typing import List, Dict, Tuple
from rich.console import Console
from seerAD.core.session import session
from seerAD.tool_handler.helper import impacket_identity, resolve_flags, run_tool

console = Console()

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
    }
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

        run_tool(cmd, env=env)

    except Exception as e:
        console.print(f"[red]{tool} error: {e}[/]")
