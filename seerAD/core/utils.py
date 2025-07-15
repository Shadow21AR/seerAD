import subprocess, shutil, os, hashlib, asyncio, json
from pathlib import Path
from impacket.krb5.crypto import _enctype_table
from impacket.krb5.types import Principal
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1
from urllib.parse import quote_plus
from rich.console import Console

from minikerberos.common.creds import KerberosCredential
from minikerberos.common.target import KerberosTarget
from minikerberos.aioclient import AIOKerberosClient
from minikerberos.protocol.errors import KerberosError
from minikerberos.common.factory import KerberosClientFactory

from seerAD.config import LOOT_DIR, ROOT_DIR
from seerAD.core.session import session

console = Console()

def get_faketime_string(dc_ip: str) -> str:
    try:
        output = subprocess.check_output(["ntpdate", "-q", dc_ip], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            parts = line.strip().split()    
            if len(parts) >= 2:
                date_str, time_str = parts[0], parts[1]
                return f"{date_str} {time_str}"
        return None
    except Exception as e:
        return None

def run_gettgt(domain, username, password=None, ntlm=None, dc_ip=None):
    if not shutil.which("getTGT.py"):
        console.print("→ Install Impacket and ensure it's accessible: [bold green]pipx install impacket[/]")
        return False, "getTGT.py not found in PATH"

    faketime_str = get_faketime_string(dc_ip) if dc_ip else None
    if not faketime_str:
        return False, f"Unable to fetch time from {dc_ip} for faketime"

    temp_ccache = f"{username}.ccache"
    env = os.environ.copy()
    env["KRB5CCNAME"] = temp_ccache
    user_spec = f"{domain}/{username}"
    cmd = ["faketime", faketime_str, "getTGT.py"]

    if password:
        user_spec += f":{password}"
    elif ntlm:
        cmd += ["-hashes", f":{ntlm}"]
    else:
        return False, "No password or NTLM hash provided"

    cmd += [user_spec]

    if dc_ip:
        cmd += ["-dc-ip", dc_ip]

    console.print(f"[cyan]→ Running:[/] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, env=env)

        if Path(temp_ccache).exists():
            label = session.current_target_label
            out_dir = LOOT_DIR / label / "tickets"
            out_dir.mkdir(parents=True, exist_ok=True)
            final_path = out_dir / f"{username}.ccache"
            shutil.move(temp_ccache, final_path)
            return True, str(final_path)
        else:
            return False, f"Expected ticket at {temp_ccache} not found"

    except subprocess.CalledProcessError as e:
        err_out = e.stderr.decode() if e.stderr else str(e)
        console.print(f"[red]✘ Command failed:[/]\n{err_out}")
        return False, err_out

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

            TIMEWRAP_FILE = LOOT_DIR / "timewrap.json"
            if not TIMEWRAP_FILE.exists():
                console.print("[yellow]ℹ Timewrap not set. Please set it first using 'timewrap set'[/]")
                return False, "Timewrap not set"

            with open(TIMEWRAP_FILE, "r") as f:
                timewrap = json.load(f)
                if timewrap.get("dc_ip") != dc_ip:
                    console.print("[yellow]ℹ DC IP in timewrap does not match target DC IP. Please set it first using 'timewrap set'[/]")
                    return False, "DC IP in timewrap does not match target DC IP"

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
    async def do_fetch():
        try:
            principal = f"{username}@{domain.upper()}"

            cred = KerberosCredential(
                principal,
                certificate=cert_path,
                key=key_path
            )

            target = KerberosTarget()
            target.domain = domain
            target.hostname = domain
            target.endpoint_ip = dc_ip
            client = AIOKerberosClient(cred, target)
            await client.get_TGT()

            label = session.current_target_label
            out_dir = LOOT_DIR / label / "tickets"
            out_dir.mkdir(parents=True, exist_ok=True)
            final_path = out_dir / f"{username}.ccache"
            client.ccache.to_file(str(final_path))
            return True, str(final_path)
        except KerberosError as e:
            return False, f"Kerberos error: {e}"
        except Exception as e:
            return False, str(e)

    return asyncio.run(do_fetch())
