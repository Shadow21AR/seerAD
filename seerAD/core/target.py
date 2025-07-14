from datetime import datetime

class Target:
    def __init__(self, label: str, ip: str, domain: str = None, hostname: str = None, fqdn: str = None, os: str = "Unknown", created_at: str = None, updated_at: str = None):
        self.label = label
        self.ip = ip
        self.domain = domain
        self.hostname = hostname
        self.fqdn = fqdn
        self.os = os
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or self.created_at

    def update(self, **kwargs):
        updated = False
        for k, v in kwargs.items():
            if hasattr(self, k):
                if getattr(self, k) != v:
                    setattr(self, k, v)
                    updated = True
        if updated:
            self.updated_at = datetime.utcnow().isoformat()
        return updated

    def to_dict(self):
        return {
            "label": self.label,
            "ip": self.ip,
            "domain": self.domain,
            "hostname": self.hostname,
            "fqdn": self.fqdn,
            "os": self.os,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict):
        return Target(
            label=data.get("label"),
            ip=data.get("ip"),
            domain=data.get("domain"),
            hostname=data.get("hostname"),
            fqdn=data.get("fqdn"),
            os=data.get("os", "Unknown"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
