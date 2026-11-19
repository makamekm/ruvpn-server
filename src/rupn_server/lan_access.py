from __future__ import annotations

from ipaddress import IPv4Network, ip_address, ip_network


class LanAccess:
    """Which private subnets remote clients may reach through the tunnel.

    Off by default so cloud servers never expose their provider network.
    RUPN_LAN_ACCESS=true turns it on; RUPN_LAN_SUBNETS lists CIDRs, and when
    it is empty the /24 around a private DNS server (the home router) is used.
    """

    @staticmethod
    def resolve(enabled: bool, configured_subnets: str, dns_server: str) -> str:
        if not enabled:
            return ""
        subnets = [s for s in (LanAccess._private_network(part) for part in configured_subnets.split(",")) if s]
        if not subnets:
            derived = LanAccess._subnet_around(dns_server)
            if derived:
                subnets = [derived]
        return ",".join(str(subnet) for subnet in subnets)

    @staticmethod
    def _private_network(raw: str) -> IPv4Network | None:
        text = raw.strip()
        if not text:
            return None
        try:
            network = ip_network(text, strict=False)
        except ValueError:
            return None
        if network.version != 4 or not network.is_private or network.is_loopback or network.is_link_local:
            return None
        return network

    @staticmethod
    def _subnet_around(dns_server: str) -> IPv4Network | None:
        host = dns_server.strip()
        if host.count(":") == 1:
            host = host.rsplit(":", 1)[0]
        try:
            address = ip_address(host)
        except ValueError:
            return None
        if address.version != 4 or not address.is_private or address.is_loopback or address.is_link_local:
            return None
        return ip_network(f"{address}/24", strict=False)
