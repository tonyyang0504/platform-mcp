"""Outbound URL guard for URLs that do not come from the catalog: a tool argument the runtime downloads
(multipart ``file:<arg>`` parts) and the forge's spec fetches. Such a URL may come from a model that read
attacker-controlled text, so it must not reach the machine's own network: loopback, private ranges,
link-local (cloud metadata at 169.254.169.254), carrier-grade NAT, multicast, reserved and documentation
ranges, and IPv6 equivalents (including IPv4 embedded in mapped, NAT64 and 6to4 addresses).

The host is resolved and EVERY address must be public; a host that does not resolve is refused (fail
closed). The caller then connects to the vetted address itself (``pin``: the IP in the URL, the original
Host header and TLS server name), so a DNS answer that changes after the check (rebinding) is never used.
Redirects are followed by the caller one hop at a time, each hop checked and pinned again.
``PLATFORM_MCP_ALLOW_PRIVATE_URLS=1`` turns the guard off (a local mock, a private network on purpose).

The TypeScript runtime's netguard.ts applies the same table; tests/fixtures/netguard_cases.json is
checked against both."""

import asyncio
import ipaddress
import os
import socket
from typing import Awaitable, Callable

from .errors import InvalidInput

ALLOW_ENV = "PLATFORM_MCP_ALLOW_PRIVATE_URLS"

_BLOCKED_V4 = [ipaddress.ip_network(n) for n in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24",
    "192.0.2.0/24", "192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
    "224.0.0.0/4", "240.0.0.0/4")]
_BLOCKED_V6 = [ipaddress.ip_network(n) for n in (
    "::/96", "100::/64", "2001:db8::/32", "fc00::/7", "fe80::/10", "fec0::/10", "ff00::/8")]
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_SIX_TO_FOUR = ipaddress.ip_network("2002::/16")

Resolver = Callable[[str], Awaitable[list[str]]]


def is_public_ip(text: str) -> bool:
    """True only for a literal IPv4/IPv6 address outside every blocked range."""
    try:
        ip = ipaddress.ip_address(str(text).split("%", 1)[0].strip("[]"))
    except ValueError:
        return False
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            return is_public_ip(str(ip.ipv4_mapped))
        if ip in _NAT64:
            return is_public_ip(str(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)))
        if ip in _SIX_TO_FOUR:
            return is_public_ip(str(ipaddress.IPv4Address((int(ip) >> 80) & 0xFFFFFFFF)))
        return not any(ip in n for n in _BLOCKED_V6)
    return not any(ip in n for n in _BLOCKED_V4)


async def default_resolver(host: str) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


def _host_of(url: str) -> tuple[str, str]:
    """(scheme, host) parsed the way httpx parses the URL it will fetch."""
    import httpx
    try:
        u = httpx.URL(url)
    except Exception:
        return "", ""
    host = u.raw_host.decode("ascii", "replace") if u.raw_host else ""
    return u.scheme.lower(), host.strip("[]").lower()


async def check_url(url: str, resolver: Resolver | None = None, *, what: str = "URL") -> list[str] | None:
    """Raise InvalidInput unless ``url`` is http(s) and every address its host resolves to is public. Returns the
    vetted addresses to connect to (``pin``), or None when the operator turned the guard off."""
    if os.environ.get(ALLOW_ENV) == "1":
        return None
    scheme, host = _host_of(str(url))
    if scheme not in ("http", "https") or not host:
        raise InvalidInput(f"{what} must be an http(s) URL with a host")
    if host == "localhost" or host.endswith(".localhost"):
        raise InvalidInput(f"{what} points at this machine (localhost); set {ALLOW_ENV}=1 to allow private addresses")
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
        addresses = [host]
    except ValueError:
        try:
            addresses = await (resolver or default_resolver)(host)
        except (OSError, UnicodeError, ValueError):
            addresses = []
        if not addresses:
            raise InvalidInput(f"{what}: the host does not resolve")
    if not all(is_public_ip(a) for a in addresses):
        raise InvalidInput(f"{what} resolves to a private, loopback, link-local or reserved address; set {ALLOW_ENV}=1 to allow it")
    return [a.split("%", 1)[0] for a in addresses]


def pick(addresses: list[str]) -> str:
    """The address to connect to: the first IPv4 one (hosts without IPv6 routes are common), else the first."""
    return next((a for a in addresses if "." in a and ":" not in a), addresses[0])


def pin(url: str, addresses: list[str] | None) -> tuple[str, dict, dict]:
    """(url with the vetted IP as host, headers, request extensions): the connection goes to that address while
    the Host header and the TLS server name (certificate check) stay the original host. No addresses: unchanged."""
    import httpx
    if not addresses:
        return url, {}, {}
    u = httpx.URL(url)
    host = u.host
    target = u.copy_with(host=pick(addresses))
    headers = {"Host": u.netloc.decode("ascii")}
    return str(target), headers, ({"sni_hostname": host} if u.scheme == "https" else {})
