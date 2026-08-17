"""Bounded, allowlisted and SSRF-resistant retrieval of normative sources.

Source retrieval is deliberately a small infrastructure boundary. It does not
create a curriculum revision and it never turns downloaded bytes into a
published rule. Callers must persist the returned bytes as an immutable source
snapshot and route any semantic interpretation through governance review.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import socket
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from ssl import SSLContext, create_default_context
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from django.conf import settings

DEFAULT_MAX_SOURCE_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 3
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_SOURCE_URL_LENGTH = 2_048
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_ALLOWED_SCHEMES = frozenset({"https"})
_UNSAFE_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".intranet",
    ".home.arpa",
)


class SourceFetchError(ValueError):
    """Raised when a source cannot be fetched under the safety policy."""


@dataclass(frozen=True, slots=True)
class SourceFetchPolicy:
    """Explicit egress policy for one source-fetch operation."""

    allowed_hosts: frozenset[str] = frozenset()
    allowed_schemes: frozenset[str] = _ALLOWED_SCHEMES
    max_bytes: int = DEFAULT_MAX_SOURCE_BYTES
    max_redirects: int = DEFAULT_MAX_REDIRECTS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_settings(cls) -> SourceFetchPolicy:
        hosts = frozenset(
            item.strip().lower()
            for item in str(getattr(settings, "SOURCE_FETCH_ALLOWED_HOSTS", "")).split(",")
            if item.strip()
        )
        configured_schemes = frozenset(
            item.strip().lower()
            for item in str(
                getattr(settings, "SOURCE_FETCH_ALLOWED_SCHEMES", ",".join(_ALLOWED_SCHEMES))
            ).split(",")
            if item.strip()
        )
        return cls(
            allowed_hosts=hosts,
            allowed_schemes=configured_schemes or _ALLOWED_SCHEMES,
            max_bytes=int(getattr(settings, "SOURCE_FETCH_MAX_BYTES", DEFAULT_MAX_SOURCE_BYTES)),
            max_redirects=int(
                getattr(settings, "SOURCE_FETCH_MAX_REDIRECTS", DEFAULT_MAX_REDIRECTS)
            ),
            timeout_seconds=float(
                getattr(settings, "SOURCE_FETCH_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            ),
        )


@dataclass(frozen=True, slots=True)
class ValidatedSourceURL:
    url: str
    scheme: str
    hostname: str
    port: int
    host_header: str
    addresses: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True, slots=True)
class SourceFetchResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True, slots=True)
class FetchedSource:
    content: bytes
    final_url: str
    status: int
    mime_type: str
    sha256: str
    redirect_count: int


Resolver = Callable[[str, int], Sequence[tuple[Any, ...]]]
Transport = Callable[[ValidatedSourceURL, SourceFetchPolicy], SourceFetchResponse]


def _normalise_hostname(hostname: str) -> str:
    try:
        normalized = hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise SourceFetchError("The source hostname is not valid IDNA") from exc
    if not normalized or "\x00" in normalized:
        raise SourceFetchError("The source hostname is invalid")
    return normalized


def _is_unsafe_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    mapped = getattr(address, "ipv4_mapped", None)
    effective = mapped or address
    return bool(
        not effective.is_global
        or effective.is_private
        or effective.is_loopback
        or effective.is_link_local
        or effective.is_multicast
        or effective.is_reserved
        or effective.is_unspecified
        or bool(getattr(effective, "is_site_local", False))
    )


def _host_is_allowed(hostname: str, allowed_hosts: frozenset[str]) -> bool:
    if not allowed_hosts:
        return False
    for raw_entry in allowed_hosts:
        entry = _normalise_hostname(raw_entry.removeprefix("*."))
        if raw_entry.startswith("*."):
            if hostname.endswith(f".{entry}") and hostname != entry:
                return True
        elif hostname == entry:
            return True
    return False


def _resolve_public_addresses(
    hostname: str, port: int, resolver: Resolver | None = None
) -> tuple[tuple[Any, ...], ...]:
    resolve = resolver or socket.getaddrinfo
    try:
        records = resolve(hostname, port)
    except (OSError, socket.gaierror) as exc:
        raise SourceFetchError("The source hostname could not be resolved") from exc
    addresses: list[tuple[Any, ...]] = []
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        if len(record) < 5:
            continue
        sockaddr = tuple(record[4])
        try:
            address = ipaddress.ip_address(str(sockaddr[0]))
        except ValueError as exc:
            raise SourceFetchError("The source resolved to an invalid address") from exc
        if _is_unsafe_ip(address):
            raise SourceFetchError("The source resolves to a private or reserved network")
        if sockaddr not in seen:
            seen.add(sockaddr)
            addresses.append(sockaddr)
    if not addresses:
        raise SourceFetchError("The source hostname has no usable address")
    return tuple(addresses)


def validate_source_url(
    url: str,
    *,
    policy: SourceFetchPolicy | None = None,
    resolver: Resolver | None = None,
) -> ValidatedSourceURL:
    """Validate a source URL and resolve every address before connecting."""

    active_policy = policy or SourceFetchPolicy.from_settings()
    if not isinstance(url, str) or not url or len(url) > MAX_SOURCE_URL_LENGTH:
        raise SourceFetchError("The source URL is missing or too long")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise SourceFetchError("The source URL has an invalid port") from exc
    scheme = parts.scheme.lower()
    if scheme not in active_policy.allowed_schemes:
        raise SourceFetchError("Only explicitly allowed HTTP(S) schemes are supported")
    if parts.username is not None or parts.password is not None:
        raise SourceFetchError("Source URLs cannot contain credentials")
    if parts.fragment:
        raise SourceFetchError("Source URLs cannot contain fragments")
    if not parts.hostname:
        raise SourceFetchError("The source URL must contain a hostname")
    hostname = _normalise_hostname(parts.hostname)
    if hostname == "localhost" or hostname.endswith(_UNSAFE_HOST_SUFFIXES):
        raise SourceFetchError("Local and internal source hostnames are not allowed")
    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        literal_address = None
    if literal_address is not None and _is_unsafe_ip(literal_address):
        raise SourceFetchError("private or non-global source addresses are not allowed")
    if not _host_is_allowed(hostname, active_policy.allowed_hosts):
        raise SourceFetchError("The source hostname is not on the configured allowlist")
    default_port = 443 if scheme == "https" else 80
    resolved_port = port or default_port
    if resolved_port != default_port:
        raise SourceFetchError("Only the default HTTP(S) port is allowed")
    addresses = _resolve_public_addresses(hostname, resolved_port, resolver)
    netloc = hostname
    if ":" in hostname and not hostname.startswith("["):
        netloc = f"[{hostname}]"
    if port is not None:
        netloc = f"{netloc}:{resolved_port}"
    normalized_url = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    host_header = hostname if port is None else f"{hostname}:{resolved_port}"
    return ValidatedSourceURL(
        url=normalized_url,
        scheme=scheme,
        hostname=hostname,
        port=resolved_port,
        host_header=host_header,
        addresses=addresses,
    )


def _read_bounded_body(body: bytes, *, max_bytes: int) -> bytes:
    if len(body) > max_bytes:
        raise SourceFetchError("The source response exceeds the configured size limit")
    return body


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, hostname: str, port: int, address: tuple[Any, ...], timeout: float) -> None:
        super().__init__(hostname, port=port, timeout=timeout)
        self._pinned_address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(self._pinned_address, self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        hostname: str,
        port: int,
        address: tuple[Any, ...],
        timeout: float,
        context: SSLContext,
    ) -> None:
        super().__init__(hostname, port=port, timeout=timeout, context=context)
        self._pinned_address = address
        self._ssl_context = context

    def connect(self) -> None:
        raw_socket = socket.create_connection(self._pinned_address, self.timeout)
        self.sock = self._ssl_context.wrap_socket(raw_socket, server_hostname=self.host)


def _request_over_pinned_socket(
    target: ValidatedSourceURL, policy: SourceFetchPolicy
) -> SourceFetchResponse:
    path = urlsplit(target.url)
    request_target = path.path or "/"
    if path.query:
        request_target = f"{request_target}?{path.query}"
    last_error: Exception | None = None
    for address in target.addresses:
        connection: http.client.HTTPConnection | None = None
        try:
            if target.scheme == "https":
                connection = _PinnedHTTPSConnection(
                    target.hostname,
                    target.port,
                    address,
                    policy.timeout_seconds,
                    create_default_context(),
                )
            else:
                connection = _PinnedHTTPConnection(
                    target.hostname, target.port, address, policy.timeout_seconds
                )
            connection.request(
                "GET",
                request_target,
                headers={
                    "Accept": "application/pdf,application/json,text/plain;q=0.9,*/*;q=0.1",
                    "Connection": "close",
                    "Host": target.host_header,
                    "User-Agent": "curriculum-navigator-source-fetch/1.0",
                },
            )
            response = connection.getresponse()
            encoding = (response.getheader("Content-Encoding") or "").strip().lower()
            if encoding not in {"", "identity"}:
                raise SourceFetchError("Compressed source responses are not accepted")
            declared_length = response.getheader("Content-Length")
            if declared_length:
                try:
                    if int(declared_length) > policy.max_bytes:
                        raise SourceFetchError(
                            "The source response exceeds the configured size limit"
                        )
                except ValueError as exc:
                    raise SourceFetchError("The source response length is invalid") from exc
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(64 * 1024, policy.max_bytes - total + 1))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > policy.max_bytes:
                    raise SourceFetchError("The source response exceeds the configured size limit")
            return SourceFetchResponse(
                status=response.status,
                headers={key: value for key, value in response.getheaders()},
                body=b"".join(chunks),
            )
        except SourceFetchError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            if connection is not None:
                connection.close()
    raise SourceFetchError("The source connection failed") from last_error


class SafeSourceFetcher:
    """Fetch an allowlisted source with explicit, validated redirects only."""

    def __init__(self, *, transport: Transport | None = None) -> None:
        self._transport = transport

    def fetch(
        self,
        url: str,
        *,
        policy: SourceFetchPolicy | None = None,
        resolver: Resolver | None = None,
    ) -> FetchedSource:
        active_policy = policy or SourceFetchPolicy.from_settings()
        if active_policy.max_bytes < 1 or active_policy.max_redirects < 0:
            raise SourceFetchError("Source fetch limits must be positive")
        current = validate_source_url(url, policy=active_policy, resolver=resolver)
        redirects = 0
        while True:
            response = (
                self._transport(current, active_policy)
                if self._transport is not None
                else _request_over_pinned_socket(current, active_policy)
            )
            if response.status in _REDIRECT_STATUSES:
                location = response.headers.get("Location", "").strip()
                if not location:
                    raise SourceFetchError("The source redirect has no Location")
                redirects += 1
                if redirects > active_policy.max_redirects:
                    raise SourceFetchError("The source redirect limit was exceeded")
                current = validate_source_url(
                    urljoin(current.url, location), policy=active_policy, resolver=resolver
                )
                continue
            if response.status < 200 or response.status >= 300:
                raise SourceFetchError("The source returned an unsuccessful status")
            content = _read_bounded_body(response.body, max_bytes=active_policy.max_bytes)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
            return FetchedSource(
                content=content,
                final_url=current.url,
                status=response.status,
                mime_type=content_type or "application/octet-stream",
                sha256=hashlib.sha256(content).hexdigest(),
                redirect_count=redirects,
            )


__all__ = [
    "DEFAULT_MAX_REDIRECTS",
    "DEFAULT_MAX_SOURCE_BYTES",
    "FetchedSource",
    "SafeSourceFetcher",
    "SourceFetchError",
    "SourceFetchPolicy",
    "SourceFetchResponse",
    "ValidatedSourceURL",
    "validate_source_url",
]
