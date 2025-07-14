import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from seerAD.config import LOOT_DIR, DATA_DIR
from seerAD.core import creds
from ipaddress import ip_address, AddressValueError
from datetime import datetime

class Session:
    def __init__(self):
        self.targets: Dict[str, Dict[str, Any]] = {}
        self.current_target_label: Optional[str] = None
        self.current_credential_index: Optional[int] = None
        self.ensure_workspace()
        self.load_session()

    def ensure_workspace(self) -> None:
        """Ensure all required directories exist and session is initialized."""

        # Create required directories if they don't exist
        LOOT_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize empty session if one doesn't exist
        session_file = LOOT_DIR / "session.json"
        if not session_file.exists():
            self.reset()
            self.save_session()

    def _session_file(self) -> Path:
        return LOOT_DIR / "session.json"

    def load_session(self):
        path = self._session_file()
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.targets = data.get("targets", {})
                self.current_target_label = data.get("current_target_label")
                self.current_credential_index = data.get("current_credential_index")
            except Exception:
                self.targets = {}
                self.current_target_label = None
                self.current_credential_index = None
        else:
            self.targets = {}
            self.current_target_label = None
            self.current_credential_index = None

    def save_session(self):
        path = self._session_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "targets": self.targets,
            "current_target_label": self.current_target_label,
            "current_credential_index": self.current_credential_index,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def reset(self):
        self.targets = {}
        self.current_target_label = None
        self.current_credential_index = None

    def save(self):
        self.save_session()

    # Target management
    def validate_ip(self, ip: str) -> bool:
        try:
            ip_address(ip)
            return True
        except AddressValueError:
            return False

    def list_targets(self) -> Dict[str, Dict[str, Any]]:
        return self.targets

    def add_target(self, label: str, target_info: Dict[str, Any]) -> None:
        self.targets[label] = target_info
        self.save_session()

    def delete_target(self, label: str) -> bool:
        if label in self.targets:
            del self.targets[label]
            # Remove creds.json for target
            creds_path = LOOT_DIR / label / "creds.json"
            if creds_path.exists():
                creds_path.unlink()

            if self.current_target_label == label:
                self.current_target_label = None
                self.current_credential_index = None
            self.save_session()
            return True
        return False

    def switch_target(self, label: str) -> bool:
        if label in self.targets:
            self.current_target_label = label
            self.current_credential_index = None
            self.save_session()
            return True
        return False

    def set_current_target(self, label: str) -> bool:
        return self.switch_target(label)

    def update_current_target(self, **kwargs) -> bool:
        if not self.current_target_label or self.current_target_label not in self.targets:
            return False
        target = self.targets[self.current_target_label]
        updated = False
        for key, value in kwargs.items():
            if target.get(key) != value:
                target[key] = value
                updated = True
        if updated:
            target['updated_at'] = datetime.utcnow().isoformat()
            self.save_session()
        return updated

    @property
    def current_target(self) -> Optional[Dict[str, Any]]:
        if self.current_target_label:
            return self.targets.get(self.current_target_label)
        return None

    # Credential management delegating to core.creds
    def get_credentials(self, label: Optional[str] = None, username: Optional[str] = None, auth_type: Optional[str] = None) -> List[Dict[str, Any]]:
        label = label or self.current_target_label
        if not label:
            return []
        return creds.get_credentials(label, username=username, auth_type=auth_type)

    def add_credential(self, label: str, cred_data: Dict[str, Any]) -> bool:
        return creds.add_credential(label, cred_data)

    def delete_credential(self, label: str, username: str, auth_type: Optional[str] = None) -> bool:
        return creds.delete_credential(label, username, auth_type)

    # Current credential tracking by index (in the credentials list)
    def use_credential(self, index: int) -> bool:
        creds_list = self.get_credentials(self.current_target_label)
        if 0 <= index < len(creds_list):
            self.current_credential_index = index
            self.save_session()
            return True
        return False

    @property
    def current_credential(self) -> Optional[Dict[str, Any]]:
        if self.current_target_label is None or self.current_credential_index is None:
            return None
        creds_list = self.get_credentials(self.current_target_label)
        if 0 <= self.current_credential_index < len(creds_list):
            return creds_list[self.current_credential_index]
        return None

# Global singleton
session = Session()

# Convenience proxy for current session
def current_session():
    return session
