from __future__ import annotations

from ipaddress import ip_address
from pathlib import Path


class ServerDnsResolver:
    @staticmethod
    def resolve(configured_dns: str = "", resolv_conf_path: Path = Path("/etc/resolv.conf")) -> str:
        configured = configured_dns.strip()
        if configured:
            return ServerDnsResolver._with_port(configured)

        nameservers = ServerDnsResolver._nameservers(resolv_conf_path)
        for nameserver in nameservers:
            if ServerDnsResolver._is_ipv4(nameserver):
                return ServerDnsResolver._with_port(nameserver)
        if nameservers:
            return ServerDnsResolver._with_port(nameservers[0])
        return "1.1.1.1:53"

    @staticmethod
    def _nameservers(resolv_conf_path: Path) -> list[str]:
        try:
            lines = resolv_conf_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return []
        nameservers: list[str] = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2 or parts[0] != "nameserver":
                continue
            nameserver = parts[1].strip()
            if nameserver:
                nameservers.append(nameserver)
        return nameservers

    @staticmethod
    def _is_ipv4(nameserver: str) -> bool:
        host = nameserver.strip()
        if host.startswith("[") and "]" in host:
            host = host[1:host.index("]")]
        elif host.count(":") == 1:
            host = host.rsplit(":", 1)[0]
        try:
            return ip_address(host).version == 4
        except ValueError:
            return False

    @staticmethod
    def _with_port(nameserver: str) -> str:
        if nameserver.startswith("[") and "]:" in nameserver:
            return nameserver
        if nameserver.count(":") > 1:
            return f"[{nameserver}]:53"
        if ":" in nameserver:
            return nameserver
        return f"{nameserver}:53"
