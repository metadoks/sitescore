from __future__ import annotations

from .db import CommerceStore
from .delivery import DeliveryService, DeliveryStore, PostmarkGateway, SiteScoreDeliveryGateway
from .settings import Settings


def build_runtime_delivery_service(settings: Settings, store: CommerceStore) -> DeliveryService:
    return DeliveryService(
        settings=settings,
        store=DeliveryStore(store),
        sitescore=SiteScoreDeliveryGateway(settings),
        postmark=PostmarkGateway(settings),
    )
