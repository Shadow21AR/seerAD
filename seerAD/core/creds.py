import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from seerAD.config import LOOT_DIR

class Credential:
    def __init__(self, username, domain=None, password=None, ntlm=None, aes=None, ticket=None, cert=None, token=None, notes=None, created_at=None, updated_at=None):
        self.username = username
        self.domain = domain
        self.password = password
        self.ntlm = ntlm
        self.aes = aes
        self.ticket = ticket
        self.cert = cert
        self.token = token
        self.notes = notes or ""
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or self.created_at

    def update(self, **kwargs):
        changed = False
        for k, v in kwargs.items():
            if hasattr(self, k) and getattr(self, k) != v:
                setattr(self, k, v)
                changed = True
        if changed:
            self.updated_at = datetime.now(timezone.utc).isoformat()
        return changed

    def to_dict(self): return self.__dict__

    @classmethod
    def from_dict(cls, data): return cls(**data)

class CredentialManager:
    def __init__(self, target_label):
        self.target_label = target_label
        self.credentials_file = LOOT_DIR / target_label / "credentials.json"
        self.credentials: Dict[str, Credential] = {}
        self._load()

    def _key(self, username): return username.lower()

    def _load(self):
        if not self.credentials_file.exists():
            return
        try:
            with open(self.credentials_file) as f:
                data = json.load(f)
            if isinstance(data, list):  # old format
                self.credentials = {
                    self._key(c.get("username", "")): Credential.from_dict(c)
                    for c in data if c.get("username")
                }
                self._save()
            else:
                self.credentials = {
                    self._key(u): Credential.from_dict(c)
                    for u, c in data.items()
                }
        except Exception as e:
            self.credentials = {}

    def _save(self):
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        data = {u: c.to_dict() for u, c in self.credentials.items()}
        with open(self.credentials_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_credential(self, **kwargs):
        k = self._key(kwargs.get("username"))
        if k in self.credentials: return False
        self.credentials[k] = Credential(**kwargs)
        self._save()
        return True

    def update_credential(self, username, **kwargs):
        k = self._key(username)
        if k not in self.credentials: return False
        if self.credentials[k].update(**kwargs):
            self._save()
            return True
        return False

    def delete_credential(self, username):
        k = self._key(username)
        if k in self.credentials:
            del self.credentials[k]
            self._save()
            return True
        return False

    def get_credential(self, username):
        c = self.credentials.get(self._key(username))
        return c.to_dict() if c else None

    def get_all_credentials(self): return [c.to_dict() for c in self.credentials.values()]
    def get_credentials_by_domain(self, domain): 
        return [c.to_dict() for c in self.credentials.values() if c.domain and c.domain.lower() == domain.lower()]

# Backward-compatible helpers
def save_credentials(label: str, creds_data: List[Dict[str, Any]]):
    cm = CredentialManager(label)
    for cd in creds_data:
        cm.add_credential(**cd)

def get_credentials(label: str, username: Optional[str] = None):
    cm = CredentialManager(label)
    return [cm.get_credential(username)] if username else cm.get_all_credentials()

def add_credential(label: str, cred_data: Dict[str, Any]):
    return CredentialManager(label).add_credential(**cred_data)

def delete_credential(label: str, username: str):
    return CredentialManager(label).delete_credential(username)