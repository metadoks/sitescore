from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .db import CommerceStore, PersistenceUnavailable, utcnow
from .delivery import DeliveryGrantRow


class DeliveryGrantNotFound(LookupError):
    pass


def revoke_delivery_grant(store: CommerceStore, grant_id: UUID) -> bool:
    """Durably revoke one capability grant without changing payment/report truth.

    Returns True only for the first revocation. Replays are idempotent. The raw
    capability token is neither required nor recoverable from this operation.
    """
    try:
        with store.session_factory.begin() as session:
            grant = session.execute(
                select(DeliveryGrantRow)
                .where(DeliveryGrantRow.grant_id == grant_id)
                .with_for_update()
            ).scalar_one_or_none()
            if grant is None:
                raise DeliveryGrantNotFound("delivery grant not found")
            if grant.revoked_at is not None:
                return False
            now = utcnow()
            grant.revoked_at = now
            grant.updated_at = now
            return True
    except DeliveryGrantNotFound:
        raise
    except SQLAlchemyError as exc:
        raise PersistenceUnavailable("delivery grant revocation is unavailable") from exc
