from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import secrets
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import ConsumerModel, ServiceApiKeyModel
from .errors import AuthenticationRequired, InvalidApiKey, InsufficientScope

ALL_SCOPES = frozenset({"analysis:write", "analysis:read", "report:write", "report:read"})
TOKEN_PREFIX = "ssk1_"


@dataclass(frozen=True, slots=True)
class AuthenticatedConsumer:
    consumer_id: UUID
    key_record_id: UUID
    scopes: frozenset[str]

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise InsufficientScope()


def _digest(secret: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), sha256).hexdigest()


def _split_token(token: str) -> tuple[str, str]:
    if not token.startswith(TOKEN_PREFIX):
        raise InvalidApiKey()
    body = token[len(TOKEN_PREFIX):]
    if "." not in body:
        raise InvalidApiKey()
    key_id, secret = body.split(".", 1)
    if not key_id or not secret:
        raise InvalidApiKey()
    return key_id, secret


def authenticate_bearer(session: Session, authorization: str | None, *, pepper: str) -> AuthenticatedConsumer:
    if authorization is None:
        raise AuthenticationRequired()
    scheme, sep, token = authorization.partition(" ")
    if not sep or scheme.lower() != "bearer" or not token:
        raise AuthenticationRequired()
    key_id, secret = _split_token(token)
    record = session.scalar(
        select(ServiceApiKeyModel).where(ServiceApiKeyModel.key_id == key_id)
    )
    if record is None or record.active is not True or record.revoked_at is not None:
        raise InvalidApiKey()
    consumer = record.consumer
    if consumer is None or consumer.active is not True:
        raise InvalidApiKey()
    expected = record.secret_digest
    actual = _digest(secret, pepper)
    if not hmac.compare_digest(expected, actual):
        raise InvalidApiKey()
    scopes = frozenset(record.scopes)
    if not scopes.issubset(ALL_SCOPES):
        raise InvalidApiKey()
    return AuthenticatedConsumer(record.consumer_id, record.record_id, scopes)


def provision_service_key(
    session: Session,
    *,
    consumer_id: UUID,
    scopes: set[str] | frozenset[str],
    pepper: str,
    now: datetime | None = None,
) -> str:
    if not scopes or not set(scopes).issubset(ALL_SCOPES):
        raise ValueError("scopes must be a non-empty subset of supported service scopes")
    consumer = session.get(ConsumerModel, consumer_id)
    if consumer is None or consumer.active is not True:
        raise ValueError("active consumer is required")
    key_id = secrets.token_urlsafe(12)
    secret = secrets.token_urlsafe(32)
    record = ServiceApiKeyModel(
        key_id=key_id,
        consumer_id=consumer_id,
        secret_digest=_digest(secret, pepper),
        scopes=sorted(scopes),
        active=True,
        created_at=now or datetime.now(timezone.utc),
        revoked_at=None,
    )
    session.add(record)
    session.flush()
    return f"{TOKEN_PREFIX}{key_id}.{secret}"
