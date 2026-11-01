"""Keeps normal users from making the server fetch addresses in the local network.

On a public instance an invited user could otherwise let Tubesy (and yt-dlp)
request e.g. the router's web interface. Administrators are always allowed;
for users it is the setting allow_local_urls. Redirects that yt-dlp follows
later are not covered – this is a first line, not a sandbox.
"""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import User
from . import settings as app_settings

LOCAL_NOT_ALLOWED = "Links zu lokalen Adressen sind nicht erlaubt"


def _is_local_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value.split("%", 1)[0])
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return not ip.is_global or ip.is_multicast


async def is_local(url: str) -> bool:
    """True when the host of the URL is or resolves to a non-public address."""
    host = urlsplit(url).hostname
    if not host:
        return False
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa")):
        return True
    try:
        return _is_local_ip(host)
    except ValueError:
        pass  # a name, not an address
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return False  # unknown names fail in yt-dlp anyway
    return any(_is_local_ip(info[4][0]) for info in infos)


async def ensure_allowed(db: Session, user: User, urls: list[str]) -> None:
    """Raises 403 if a normal user may not fetch one of the URLs."""
    if user.is_admin or app_settings.get(db, "allow_local_urls"):
        return
    seen: set[str] = set()
    for url in urls:
        host = urlsplit(url).hostname or ""
        if host in seen:
            continue
        seen.add(host)
        if await is_local(url):
            raise HTTPException(403, LOCAL_NOT_ALLOWED)
