from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .contracts import FulfillmentState, OrderState, PaymentState


class AutomationOrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v1"] = "v1"
    order_id: UUID
    order_state: OrderState
    payment_state: PaymentState
    fulfillment_state: FulfillmentState
    retryable: bool
    terminal: bool
    next_action: Literal["wait", "advance", "refund", "delivery", "none"]
