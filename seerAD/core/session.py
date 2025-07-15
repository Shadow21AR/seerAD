from pathlib import Path
from typing import Dict, Optional, Any, List
import json
import os
from seerAD.config import LOOT_DIR, DATA_DIR
from . import creds
from .target import Target, TargetManager

class Session:
    def __init__(self):
        self.session_file = LOOT_DIR / "session.json"
        self._credential_managers: Dict[str, creds.CredentialManager] = {}
        self.target_manager = TargetManager(self.session_file)
        self.current_credential_index: Optional[int] = None
        self._ensure_workspace()
        self._load()

    def _ensure_workspace(self):
        LOOT_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        local_bin = os.path.expanduser("~/.local/bin")
        if local_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = f"{local_bin}:{os.environ['PATH']}"

    def reset(self):
        self.target_manager = TargetManager(self.session_file)
        self.current_credential_index = None
        self._save()

    def _load(self):
        if not self.session_file.exists():
            return
        try:
            with open(self.session_file) as f:
                data = json.load(f)
            self.target_manager.targets = {
                label: Target.from_dict(label, tdata)
                for label, tdata in data.get("targets", {}).items()
            }
            self.target_manager.current_target_label = data.get("current_target_label")
            self.current_credential_index = data.get("current_credential_index")
        except Exception as e:
            print(f"[!] Error loading session.json: {e}")
            self.target_manager.targets = {}
            self.target_manager.current_target_label = None
            self.current_credential_index = None

    def _save(self):
        data = {
            "targets": {l: t.to_dict() for l, t in self.target_manager.targets.items()},
            "current_target_label": self.target_manager.current_target_label,
            "current_credential_index": self.current_credential_index
        }
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "w") as f:
            json.dump(data, f, indent=2)

    # === Target Shortcuts ===
    @property
    def targets(self): return self.target_manager.targets

    @property
    def current_target_label(self): return self.target_manager.current_target_label

    @property
    def current_target(self): 
        t = self.target_manager.get_current_target()
        return t.to_dict() if t else None

    def add_target(self, label, ip, **kwargs):
        added = self.target_manager.add_target(label, Target(label, ip, **kwargs))
        if added:
            self._save()
        return added

    def delete_target(self, label):
        (LOOT_DIR / label / "creds.json").unlink(missing_ok=True)
        if self.current_target_label == label:
            self.current_credential_index = None
        deleted = self.target_manager.delete_target(label)
        if deleted:
            self._save()
        return deleted

    def switch_target(self, label): 
        if self.target_manager.switch_target(label):
            self.current_credential_index = None
            self._save()
            return True
        return False

    def update_current_target(self, **kwargs):
        updated = self.target_manager.update_current_target(**kwargs)
        if updated:
            self._save()
        return updated

    # === Credential Handling ===
    def _get_cred_mgr(self, label=None) -> Optional[creds.CredentialManager]:
        label = label or self.current_target_label
        if not label: return None
        if label not in self._credential_managers:
            self._credential_managers[label] = creds.CredentialManager(label)
        return self._credential_managers[label]

    def get_credentials(self, label=None, username=None) -> List[Dict[str, Any]]:
        mgr = self._get_cred_mgr(label)
        if not mgr: return []
        if username:
            c = mgr.get_credential(username)
            return [c] if c else []
        return mgr.get_all_credentials()

    def add_credential(self, label, **kwargs):
        mgr = self._get_cred_mgr(label)
        added = mgr.add_credential(**kwargs) if mgr else False
        if added:
            self._save()
        return added

    def update_credential(self, label, username, **kwargs):
        mgr = self._get_cred_mgr(label)
        updated = mgr.update_credential(username, **kwargs) if mgr else False
        if updated:
            self._save()
        return updated

    def delete_credential(self, label, username):
        mgr = self._get_cred_mgr(label)
        if not mgr:
            return False

        # Reset current credential index if deleting the selected one
        if label == self.current_target_label and self.current_credential:
            if self.current_credential.get("username", "").lower() == username.lower():
                self.current_credential_index = None

        deleted = mgr.delete_credential(username)
        if deleted:
            self._save()
        return deleted

    def use_credential(self, username):
        mgr = self._get_cred_mgr()
        if not mgr:
            return False

        creds_list = mgr.get_all_credentials()
        for i, c in enumerate(creds_list):
            if c['username'].lower() == username.lower():
                self.current_credential_index = i
                ticket = c.get("ticket")

                # Handle KRB5CCNAME
                if ticket and Path(ticket).exists():
                    ticket_path = str(Path(ticket).resolve())
                    os.environ["KRB5CCNAME"] = ticket_path
                    print(f"[✔] KRB5CCNAME set to: {ticket_path}")
                else:
                    os.environ.pop("KRB5CCNAME", None)
                    print("[*] No ticket for this credential. Unsetting KRB5CCNAME.")

                self._save()
                return True

        return False

    @property
    def current_credential(self) -> Optional[Dict[str, Any]]:
        if self.current_target_label is None or self.current_credential_index is None:
            return None
        mgr = self._get_cred_mgr()
        creds_list = mgr.get_all_credentials() if mgr else []
        if 0 <= self.current_credential_index < len(creds_list):
            return creds_list[self.current_credential_index]
        return None

# Global singleton
session = Session()
def current_session(): return session