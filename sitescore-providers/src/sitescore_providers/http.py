"""Minimal provider-neutral HTTP boundary for acquisition clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import socket

from ._validation import require_nonempty_text
from .errors import ProviderUnavailableError


@dataclass(frozen=True, slots=True)
class HTTPRequest:
    method: str
    url: str
    query: tuple[tuple[str, str], ...] = ()
    headers: tuple[tuple[str, str], ...] = ()
    timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        require_nonempty_text(self.method, field_name="method")
        require_nonempty_text(self.url, field_name="url")
        if self.method != self.method.upper():
            raise ValueError("method must be uppercase")
        if not isinstance(self.query, tuple):
            raise TypeError("query must be a tuple")
        if not isinstance(self.headers, tuple):
            raise TypeError("headers must be a tuple")
        for field_name, items in (("query", self.query), ("headers", self.headers)):
            for item in items:
                if not isinstance(item, tuple) or len(item) != 2:
                    raise TypeError(f"{field_name} entries must be (name, value) tuples")
                require_nonempty_text(item[0], field_name=f"{field_name} name")
                if not isinstance(item[1], str):
                    raise TypeError(f"{field_name} value must be a string")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise TypeError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")

    @property
    def effective_url(self) -> str:
        if not self.query:
            return self.url
        return f"{self.url}?{urlencode(self.query)}"


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    status_code: int
    headers: tuple[tuple[str, str], ...]
    body: bytes

    def __post_init__(self) -> None:
        if isinstance(self.status_code, bool) or not isinstance(self.status_code, int):
            raise TypeError("status_code must be an int")
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status code")
        if not isinstance(self.headers, tuple):
            raise TypeError("headers must be a tuple")
        if not isinstance(self.body, bytes):
            raise TypeError("body must be bytes")


@runtime_checkable
class HTTPTransport(Protocol):
    def send(self, request: HTTPRequest) -> HTTPResponse:
        ...


class UrllibHTTPTransport:
    """Small stdlib transport. No retry, auth, caching, or provider semantics."""

    def send(self, request: HTTPRequest) -> HTTPResponse:
        if not isinstance(request, HTTPRequest):
            raise TypeError("request must be an HTTPRequest")
        native = Request(
            request.effective_url,
            method=request.method,
            headers=dict(request.headers),
        )
        try:
            with urlopen(native, timeout=float(request.timeout_seconds)) as response:  # noqa: S310 - explicit provider URL supplied by client
                return HTTPResponse(
                    status_code=int(response.status),
                    headers=tuple(sorted((str(k), str(v)) for k, v in response.headers.items())),
                    body=response.read(),
                )
        except HTTPError as exc:
            return HTTPResponse(
                status_code=int(exc.code),
                headers=tuple(sorted((str(k), str(v)) for k, v in exc.headers.items())) if exc.headers else (),
                body=exc.read(),
            )
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise ProviderUnavailableError("HTTP transport unavailable") from exc
