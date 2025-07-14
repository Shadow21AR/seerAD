import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from seerAD.config import LOOT_DIR
from enum import Enum
from dataclasses import dataclass

class AuthType(Enum):
    PASSWORD = "password"
    NTLM = "ntlm"
    AES = "aes"
    TICKET = "ticket"
    CERTIFICATE = "certificate"
    TOKEN = "token"

@dataclass
class Credential:
    username: str
    auth_type: AuthType
    secret: str
    domain: str = ""
    notes: str = ""

def _creds_path(target_label: str) -> Path:
    return LOOT_DIR / target_label / "creds.json"


def load_credentials(target_label: str) -> List[Dict[str, Any]]:
    path = _creds_path(target_label)
    if path.exists():
        try:
            with open(path, "r") as f:
                creds = json.load(f)
                if isinstance(creds, list):
                    return creds
        except Exception:
            return []
    return []


def save_credentials(target_label: str, creds: List[Dict[str, Any]]) -> None:
    path = _creds_path(target_label)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(creds, f, indent=2)


def get_credentials(target_label: str, username: Optional[str] = None, auth_type: Optional[str] = None) -> List[Dict[str, Any]]:
    creds = load_credentials(target_label)
    if username is not None:
        creds = [c for c in creds if c.get("username") == username]
    if auth_type is not None:
        creds = [c for c in creds if c.get("auth_type") == auth_type]
    return creds


def add_credential(target_label: str, cred_data: Dict[str, Any]) -> bool:
    creds = load_credentials(target_label)
    creds.append(cred_data)
    save_credentials(target_label, creds)
    return True


def delete_credential(target_label: str, username: str, auth_type: Optional[str] = None) -> bool:
    creds = load_credentials(target_label)
    initial_len = len(creds)
    creds = [c for c in creds if not (c.get("username") == username and (auth_type is None or c.get("auth_type") == auth_type))]
    if len(creds) < initial_len:
        save_credentials(target_label, creds)
        return True
    return False
