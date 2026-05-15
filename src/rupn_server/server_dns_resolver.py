from __future__ import annotations

from pathlib import Path


class ServerDnsResolver:
    @staticmethod
    def resolve(configured_dns: str = "", resolv_conf_path: Path = Path("/etc/resolv.conf")) -> str:
        configured = configured_dns.strip()
        if configured:
            return ServerDnsResolver._with_port(configured)

        for raw_line in resolv_conf_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2 or parts[0] != "nameserver":
                continue
            nameserver = parts[1].strip()
            if nameserver:
                return ServerDnsResolver._with_port(nameserver)

        raise RuntimeError(f"No nameserver found in {resolv_conf_path}")

    @staticmethod
    def _with_port(nameserver: str) -> str:
        if nameserver.startswith("[") and "]:" in nameserver:
            return nameserver
        if nameserver.count(":") > 1:
            return f"[{nameserver}]:53"
        if ":" in nameserver:
            return nameserver
        return f"{nameserver}:53"
