import subprocess, shutil, os, hashlib, asyncio, json, re, time, datetime, ntplib
from pathlib import Path
from impacket.krb5.crypto import _enctype_table
from impacket.krb5.types import Principal
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1
from urllib.parse import quote_plus
from rich.console import Console
from typing import Optional
from datetime import timezone

from minikerberos.common.creds import KerberosCredential
from minikerberos.common.target import KerberosTarget
from minikerberos.aioclient import AIOKerberosClient
from minikerberos.protocol.errors import KerberosError
from minikerberos.common.factory import KerberosClientFactory

from seerAD.config import LOOT_DIR, ROOT_DIR
from seerAD.core.session import session

console = Console()

def get_faketime_offset(target_ip: str) -> str:
    """
    Return the faketime offset string (e.g., '+3h') based on difference between local and DC time.
    Tries ntpdate first, falls back to ntplib if ntpdate fails.
    Returns "0" if both methods fail.
    """
    try:
        # Try ntpdate first
        try:
            offset_sec = get_ntp_offset_ntpdate(target_ip)
            if offset_sec is not None:
                return format_offset_as_faketime(offset_sec)
        except Exception as e:
            console.print(f"[yellow]ntpdate failed: {e}[/]")
        
        # Fall back to ntplib
        try:
            console.print("[yellow]Falling back to ntplib...[/]")
            offset_sec = get_ntp_offset_ntplib(target_ip)
            if offset_sec is not None:
                return format_offset_as_faketime(offset_sec)
        except Exception as e:
            console.print(f"[yellow]ntplib failed: {e}[/]")
            
        # If both methods failed
        console.print("[yellow]Using system time as fallback[/]")
        return "+0h"
        
    except Exception as e:
        console.print(f"[red]Failed to calculate time offset: {e}[/]")
        return "+0h"

def format_offset_as_faketime(offset: float) -> str:
    """
    Converts float seconds offset to faketime string like '+7h59'
    """
    sign = '+' if offset >= 0 else '-'
    abs_offset = abs(offset)
    hours = int(abs_offset // 3600)
    minutes = int((abs_offset % 3600) // 60)
    return f"{sign}{hours}h{minutes:02d}"


def get_ntp_offset_ntpdate(target_ip: str) -> float:
    """
    Uses `ntpdate -q` to get time offset with the target.
    Returns offset in seconds (can be float).
    """
    import subprocess

    result = subprocess.run(["ntpdate", "-q", target_ip], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if target_ip in line:
            parts = line.strip().split()
            return float(parts[3])
    raise ValueError("Could not parse offset from ntpdate output")

def get_ntp_offset_ntplib(target_ip: str) -> float:
    client = ntplib.NTPClient()
    response = client.request(target_ip, version=3, timeout=3)
    return response.offset

def derive_ntlm(password):
    return hashlib.new('md4', password.encode('utf-16le')).hexdigest()

def derive_aes(password, domain, username):
    salt = (domain.upper() + username).encode()
    aes128 = PBKDF2(password.encode(), salt, dkLen=16, count=4096, hmac_hash_module=SHA1)
    aes256 = PBKDF2(password.encode(), salt, dkLen=32, count=4096, hmac_hash_module=SHA1)
    return aes128.hex(), aes256.hex()

def run_gettgt(domain, username, password=None, ntlm=None, aes256=None, dc_ip=None):
    async def do_fetch():
        try:
            if not domain or not username:
                return False, "Missing domain or username"

            if not dc_ip:
                return False, "Missing DC IP (required for TGT request)"

            if password:
                proto = "kerberos+password"
                secret = password
            elif ntlm:
                proto = "kerberos+nt"
                secret = ntlm
            elif aes256:
                proto = "kerberos+aes"
                secret = aes256
            else:
                return False, "No valid secret (password/ntlm/aes256)"

            kerberos_url = f"{proto}://{domain}\\{quote_plus(username)}:{secret}@{dc_ip}"
            console.print(f"[cyan]→ Using kerberos_url:[/] {kerberos_url}")

            # Create Kerberos client and fetch ticket
            cf = KerberosClientFactory.from_url(kerberos_url)
            client = cf.get_client()
            await client.get_TGT()

            # Save ccache
            label = session.current_target_label
            out_dir = LOOT_DIR / label / "tickets"
            out_dir.mkdir(parents=True, exist_ok=True)
            final_path = out_dir / f"{username}.ccache"
            client.ccache.to_file(str(final_path))

            return True, str(final_path)

        except Exception as e:
            return False, f"Ticket fetch failed: {e}"

    return asyncio.run(do_fetch())


def run_cert_fetch(domain, username, cert_path, key_path=None, dc_ip=None):
    return "Not implemented yet"
