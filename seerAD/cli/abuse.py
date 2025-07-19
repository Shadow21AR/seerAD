import typer
from typing import List, Optional
from rich.console import Console
from seerAD.tool_handler.bloodyad_helper import run_bloodyad
from seerAD.tool_handler.certipyad_helper import run_certipy
from seerAD.tool_handler.helper import run_command
from seerAD.core.session import session

console = Console()

COMMANDS = {
    # BloodyAD tools
    "add_badsuccessor":     lambda m, a: run_bloodyad(["add", "badSuccessor"], m, ["-h"] if not a else a),
    "add_computer":         lambda m, a: run_bloodyad(["add", "computer"], m, ["-h"] if not a else a),
    "add_dcsync":           lambda m, a: run_bloodyad(["add", "dcsync"], m, ["-h"] if not a else a),
    "add_dnsrecord":        lambda m, a: run_bloodyad(["add", "dnsRecord"], m, ["-h"] if not a else a),
    "add_genericall":       lambda m, a: run_bloodyad(["add", "genericAll"], m, ["-h"] if not a else a),
    "add_groupmember":      lambda m, a: run_bloodyad(["add", "groupMember"], m, ["-h"] if not a else a),
    "add_rbcd":             lambda m, a: run_bloodyad(["add", "rbcd"], m, ["-h"] if not a else a),
    "add_shadowcreds":      lambda m, a: run_bloodyad(["add", "shadowCredentials"], m, ["-h"] if not a else a),
    "add_uac":              lambda m, a: run_bloodyad(["add", "uac"], m, ["-h"] if not a else a),
    "add_user":             lambda m, a: run_bloodyad(["add", "user"], m, ["-h"] if not a else a),
    "get_children":         lambda m, a: run_bloodyad(["get", "children"], m, a),
    "get_dnsDump":          lambda m, a: run_bloodyad(["get", "dnsDump"], m, a),
    "get_membership":       lambda m, a: run_bloodyad(["get", "membership"], m, ["-h"] if not a else a),
    "get_object":           lambda m, a: run_bloodyad(["get", "object"], m, ["-h"] if not a else a),
    "get_search":           lambda m, a: run_bloodyad(["get", "search"], m, a),
    "get_trusts":           lambda m, a: run_bloodyad(["get", "trusts"], m, a),
    "get_writable":         lambda m, a: run_bloodyad(["get", "writable"], m, a),
    "remove_dsync":         lambda m, a: run_bloodyad(["remove", "dcsync"], m, ["-h"] if not a else a),
    "remove_dnsrecord":     lambda m, a: run_bloodyad(["remove", "dnsRecord"], m, ["-h"] if not a else a),
    "remove_genericall":    lambda m, a: run_bloodyad(["remove", "genericAll"], m, ["-h"] if not a else a),
    "remove_groupmember":   lambda m, a: run_bloodyad(["remove", "groupMember"], m, ["-h"] if not a else a),
    "remove_object":        lambda m, a: run_bloodyad(["remove", "object"], m, ["-h"] if not a else a),
    "remove_rbcd":          lambda m, a: run_bloodyad(["remove", "rbcd"], m, ["-h"] if not a else a),
    "remove_shadowcreds":   lambda m, a: run_bloodyad(["remove", "shadowCredentials"], m, ["-h"] if not a else a),
    "remove_uac":           lambda m, a: run_bloodyad(["remove", "uac"], m, ["-h"] if not a else a),
    "set_object":           lambda m, a: run_bloodyad(["set", "object"], m, ["-h"] if not a else a),
    "set_owner":            lambda m, a: run_bloodyad(["set", "owner"], m, ["-h"] if not a else a),
    "set_password":         lambda m, a: run_bloodyad(["set", "password"], m, ["-h"] if not a else a),
    "set_restore":          lambda m, a: run_bloodyad(["set", "restore"], m, ["-h"] if not a else a),
    # Certipy-AD tools
    "certipy_account":      lambda m, a: run_certipy("account", m, ["-h"] if not a else a),
    "certipy_auth":         lambda m, a: run_certipy("auth", m, ["-h"] if not a else a),
    "certipy_ca":           lambda m, a: run_certipy("ca", m, ["-h"] if not a else a),
    "certipy_cert":         lambda m, a: run_certipy("cert", m, ["-h"] if not a else a),
    "certipy_find":         lambda m, a: run_certipy("find", m, ["-h"] if not a else a),
    "certipy_parse":        lambda m, a: run_certipy("parse", m, ["-h"] if not a else a),
    "certipy_forge":        lambda m, a: run_certipy("forge", m, ["-h"] if not a else a),
    "certipy_relay":        lambda m, a: run_certipy("relay", m, ["-h"] if not a else a),
    "certipy_req":          lambda m, a: run_certipy("req", m, ["-h"] if not a else a),
    "certipy_shadow":       lambda m, a: run_certipy("shadow", m, ["-h"] if not a else a),
    "certipy_template":     lambda m, a: run_certipy("template", m, ["-h"] if not a else a),
}

def list_modules():
    """List available abuse modules"""
    console.print("[cyan bold]Available Abuse Modules:[/]")
    cmds = ", ".join(sorted(COMMANDS.keys()))

    console.print(f"[green]{cmds}[/]")

def abuse_callback(ctx: typer.Context):
    """
    Handle abuse commands dynamically:
    abuse <command> <auth_method> [args...]
    """
    if not ctx.args:
        list_modules()
        return

    module = ctx.args[0]
    method = ctx.args[1] if len(ctx.args) > 1 else "anon"
    extra_args = ctx.args[2:] if len(ctx.args) > 2 else []

    if module not in COMMANDS:
        console.print(f"[red][!] Unknown command: {module}[/]\n")
        list_modules()
        return
    # Ticket fallback logic
    if method == "anon" and session.current_credential.get("ticket") and len(ctx.args) == 1:
        method = "ticket"

    try:
        run_command(module, method, extra_args, COMMANDS)
    except Exception as e:
        console.print(f"[red][!] Error: {e}[/]")