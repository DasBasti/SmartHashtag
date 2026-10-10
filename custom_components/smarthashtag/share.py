"""Resolve locations shared from a maps app into coordinates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import unquote_plus, urlparse

import aiohttp

from .const import LOGGER

# Only these hosts are fetched, so a shared link cannot make Home Assistant
# request arbitrary addresses.
ALLOWED_HOSTS = ("maps.app.goo.gl", "goo.gl", "maps.google.com", "google.com")
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
)
REQUEST_TIMEOUT = 15

_URL_RE = re.compile(r"https?://[^\s]+")
# Coordinates of the destination place, as used in the "data" part of the URL
_PLACE_RE = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")
_AT_RE = re.compile(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_COORD_RE = re.compile(r"^(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)$")


class SharedLocationError(Exception):
    """The shared text could not be turned into a location."""


@dataclass(frozen=True)
class SharedLocation:
    """A destination taken from a shared maps link."""

    latitude: float
    longitude: float
    name: str
    address: str = ""


def _host_allowed(host: str | None) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def extract_url(text: str) -> str:
    """Return the first link in a shared text."""
    match = _URL_RE.search(text)
    if match is None:
        raise SharedLocationError("no link found")
    return match.group(0)


def parse_maps_url(url: str) -> SharedLocation:
    """Extract the destination from a resolved Google Maps URL.

    Supports directions (``/maps/dir/<origin>/<destination>/data=...``) and
    place (``/maps/place/<name>/@lat,lon``) links.
    """
    parsed = urlparse(url)
    segments = [unquote_plus(s) for s in parsed.path.split("/") if s]
    name = ""
    if "dir" in segments:
        tail = segments[segments.index("dir") + 1 :]
        tail = [s for s in tail if not s.startswith("data=") and not s.startswith("@")]
        if tail:
            name = tail[-1]
    elif "place" in segments:
        place = segments[segments.index("place") + 1 :]
        if place:
            name = place[0]

    coords: tuple[float, float] | None = None
    match = _PLACE_RE.findall(parsed.path)
    if match:
        coords = (float(match[-1][0]), float(match[-1][1]))
    if coords is None:
        match = _AT_RE.findall(parsed.path)
        if match:
            coords = (float(match[-1][0]), float(match[-1][1]))
    if coords is None and name:
        # A destination typed as plain coordinates
        plain = _COORD_RE.match(name)
        if plain:
            coords = (float(plain.group(1)), float(plain.group(2)))
    if coords is None:
        raise SharedLocationError("the link contains no coordinates")

    lat, lon = coords
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise SharedLocationError("the coordinates are out of range")
    if not name or _COORD_RE.match(name):
        name = f"{lat:.5f}, {lon:.5f}"
    return SharedLocation(latitude=lat, longitude=lon, name=name)


async def async_resolve_shared_location(
    session: aiohttp.ClientSession, text: str
) -> SharedLocation:
    """Turn a shared maps link (or text containing one) into a destination."""
    url = extract_url(text)
    if not _host_allowed(urlparse(url).hostname):
        raise SharedLocationError("only Google Maps links are supported")

    try:
        async with session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            allow_redirects=True,
        ) as response:
            final_url = str(response.url)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise SharedLocationError(f"the link could not be opened ({err})") from err

    LOGGER.debug("Resolved shared link to %s", final_url.split("?")[0])
    if not _host_allowed(urlparse(final_url).hostname):
        raise SharedLocationError("the link did not lead to Google Maps")
    return parse_maps_url(final_url)
