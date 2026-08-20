from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from .db import CommerceStore, PersistenceUnavailable, StripeEventInboxRow
from .dispatcher import OutboxDispatchSettings
from .recovery import (
    ReceivedInboxCandidate,
    RecoveryClaim,
    RecoveryN8nIngressClient,
    RecoveryRuntimeSettings,
    RecoveryService,
)
from .settings import ConfigurationError, Settings
from .webhook import CheckoutEvidenceGateway, StripeCheckoutEvidenceGateway


def _safe_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except (TypeError, ValueError, AttributeError):
        return None


class LineageRecoveryService(RecoveryService):
    """Recovery service that re-proves the original signed Event correlation.

    The candidate order identifier is persisted from the verified Stripe Event in the
    durable inbox.  A stale `received` row may only be resumed for that exact order;
    recovery never infers or rewrites this lineage from later provider state.
    """

    def _stored_candidate_order_id(self, event_id: str) -> UUID | None:
        try:
            with self.store.session_factory() as session:
                row = session.get(StripeEventInboxRow, event_id)
                if row is None:
                    raise PersistenceUnavailable("recovery Stripe inbox identity is unavailable")
                return _safe_uuid(row.candidate_order_id)
        except PersistenceUnavailable:
            raise
        except SQLAlchemyError as exc:
            raise PersistenceUnavailable("recovery Stripe inbox lineage is unavailable") from exc

    def _resume_inbox(
        self,
        *,
        claim: RecoveryClaim,
        run_id: UUID,
        event: ReceivedInboxCandidate,
        now,
    ) -> tuple[str, str | None]:
        candidate_order_id = self._stored_candidate_order_id(event.event_id)
        if candidate_order_id != claim.order_id:
            self.commerce_store.mark_event_attention(event.event_id, "event_order_correlation_invalid")
            self._finish_attention(
                claim,
                run_id=run_id,
                now=now,
                action="resume_stripe_inbox",
                code="event_order_correlation_invalid",
            )
            return "attention", None
        return super()._resume_inbox(claim=claim, run_id=run_id, event=event, now=now)


def build_recovery_service(settings: Settings, store: CommerceStore) -> RecoveryService:
    runtime = RecoveryRuntimeSettings.from_env()
    dispatch_settings = OutboxDispatchSettings.from_env()
    if dispatch_settings.database_url != settings.database_url:
        raise ConfigurationError("recovery n8n dispatch database configuration mismatch")
    return LineageRecoveryService(
        settings=settings,
        runtime=runtime,
        commerce_store=store,
        evidence_gateway=StripeCheckoutEvidenceGateway(settings),
        n8n=RecoveryN8nIngressClient(dispatch_settings),
    )
