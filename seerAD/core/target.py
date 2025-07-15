import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from seerAD.config import LOOT_DIR

class Target:
    def __init__(self, label: str, ip: str, domain=None, fqdn=None, created_at=None, updated_at=None):
        self.label = label
        self.ip = ip
        self.domain = domain
        self.fqdn = fqdn
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or self.created_at
        (LOOT_DIR / label).mkdir(parents=True, exist_ok=True)

    def update(self, **kwargs):
        changed = False
        for k, v in kwargs.items():
            if hasattr(self, k) and getattr(self, k) != v:
                setattr(self, k, v)
                changed = True
        if changed:
            self.updated_at = datetime.now(timezone.utc).isoformat()
        return changed

    def to_dict(self):
        return {
            "ip": self.ip,
            "domain": self.domain,
            "fqdn": self.fqdn,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, label, data):
        data = dict(data)
        data.pop("label", None)
        return cls(label=label, **data)

class TargetManager:
    def __init__(self, session_file: Path):
        self.session_file = session_file
        self.targets: Dict[str, Target] = {}
        self.current_target_label: Optional[str] = None
        self._load()

    def _load(self):
        if not self.session_file.exists():
            return
        try:
            with open(self.session_file) as f:
                data = json.load(f)
            self.targets = {
                label: Target.from_dict(label, td)
                for label, td in data.get("targets", {}).items()
            }
            self.current_target_label = data.get("current_target_label")
        except Exception as e:
            print(f"[!] Error loading session.json: {e}")
            self.targets, self.current_target_label = {}, None

    def _save(self):
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "targets": {l: t.to_dict() for l, t in self.targets.items()},
            "current_target_label": self.current_target_label
        }
        with open(self.session_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_target(self, label, target):
        if label in self.targets: return False
        self.targets[label] = target
        self._save()
        return True

    def delete_target(self, label):
        if label not in self.targets: return False
        import shutil
        shutil.rmtree(LOOT_DIR / label, ignore_errors=True)
        del self.targets[label]
        if self.current_target_label == label:
            self.current_target_label = None
        self._save()
        return True

    def switch_target(self, label):
        if label not in self.targets: return False
        self.current_target_label = label
        self._save()
        return True

    def get_target(self, label): return self.targets.get(label)

    def get_current_target(self): 
        return self.get_target(self.current_target_label) if self.current_target_label else None

    def update_current_target(self, **kwargs):
        t = self.get_current_target()
        if not t: return False
        if t.update(**kwargs):
            self._save()
            return True
        return False
