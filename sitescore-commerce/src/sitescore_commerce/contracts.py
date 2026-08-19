from __future__ import annotations

import hashlib
import json
import math
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, TypeAdapter, field_validator, model_validator


def _non_empty_trimmed(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("value must not be blank")
    return stripped


def _strict_finite_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("value must be a JSON number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError("value must be finite") from exc
    if not math.isfinite(number):
        raise ValueError("value must be finite")
    return number


NonEmptyString = Annotated[str, BeforeValidator(_non_empty_trimmed)]
FiniteNumber = Annotated[float, BeforeValidator(_strict_finite_number)]
NonNegativeNumber = Annotated[FiniteNumber, Field(ge=0)]
PositiveNumber = Annotated[FiniteNumber, Field(gt=0)]
Fraction = Annotated[FiniteNumber, Field(ge=0, le=1)]
PositiveStrictInt = Annotated[StrictInt, Field(gt=0)]


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddressRequest(StrictRequestModel):
    country_code: Literal["US"]
    street: NonEmptyString
    city: NonEmptyString | None = None
    state: NonEmptyString | None = None
    zip_code: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_census_address_shape(self) -> "AddressRequest":
        has_zip = self.zip_code is not None
        has_city_state = self.city is not None and self.state is not None
        if not (has_zip or has_city_state):
            raise ValueError("address requires street + zip_code or street + city + state")
        return self


class OperatingCostsRequest(StrictRequestModel):
    monthly_rent: NonNegativeNumber
    fixed_labor: NonNegativeNumber
    fixed_overhead: NonNegativeNumber


class CoffeeBusinessInputs(StrictRequestModel):
    target_population: NonNegativeNumber
    target_rate: Fraction
    capture_rate_conservative: Fraction
    capture_rate_base: Fraction
    capture_rate_optimistic: Fraction
    visit_frequency_per_month: NonNegativeNumber
    average_ticket: PositiveNumber

    @model_validator(mode="after")
    def validate_capture_order(self) -> "CoffeeBusinessInputs":
        if not self.capture_rate_conservative <= self.capture_rate_base <= self.capture_rate_optimistic:
            raise ValueError("capture rates must satisfy conservative <= base <= optimistic")
        return self


class RestaurantBusinessInputs(StrictRequestModel):
    seats: PositiveStrictInt
    turnover_per_day: NonNegativeNumber
    utilization_conservative: Fraction
    utilization_base: Fraction
    utilization_optimistic: Fraction
    average_ticket: PositiveNumber
    operating_days_per_month: PositiveStrictInt

    @model_validator(mode="after")
    def validate_utilization_order(self) -> "RestaurantBusinessInputs":
        if not self.utilization_conservative <= self.utilization_base <= self.utilization_optimistic:
            raise ValueError("utilization must satisfy conservative <= base <= optimistic")
        return self


class GymBusinessInputs(StrictRequestModel):
    target_population: NonNegativeNumber
    penetration_rate_conservative: Fraction
    penetration_rate_base: Fraction
    penetration_rate_optimistic: Fraction
    usable_area: PositiveNumber
    members_per_area_unit: PositiveNumber
    monthly_membership_fee: PositiveNumber

    @model_validator(mode="after")
    def validate_penetration_order(self) -> "GymBusinessInputs":
        if not self.penetration_rate_conservative <= self.penetration_rate_base <= self.penetration_rate_optimistic:
            raise ValueError("penetration rates must satisfy conservative <= base <= optimistic")
        return self


class BeautyBusinessInputs(StrictRequestModel):
    stations: PositiveStrictInt
    operating_hours_per_week: PositiveNumber
    average_service_duration_hours: PositiveNumber
    utilization_conservative: Fraction
    utilization_base: Fraction
    utilization_optimistic: Fraction
    average_ticket: PositiveNumber

    @model_validator(mode="after")
    def validate_utilization_order(self) -> "BeautyBusinessInputs":
        if not self.utilization_conservative <= self.utilization_base <= self.utilization_optimistic:
            raise ValueError("utilization must satisfy conservative <= base <= optimistic")
        return self


class CoffeeAnalysisRequest(StrictRequestModel):
    sector: Literal["coffee"]
    location: AddressRequest
    business_inputs: CoffeeBusinessInputs
    costs: OperatingCostsRequest


class RestaurantAnalysisRequest(StrictRequestModel):
    sector: Literal["restaurant"]
    location: AddressRequest
    business_inputs: RestaurantBusinessInputs
    costs: OperatingCostsRequest


class GymAnalysisRequest(StrictRequestModel):
    sector: Literal["gym"]
    location: AddressRequest
    business_inputs: GymBusinessInputs
    costs: OperatingCostsRequest


class BeautyAnalysisRequest(StrictRequestModel):
    sector: Literal["beauty"]
    location: AddressRequest
    business_inputs: BeautyBusinessInputs
    costs: OperatingCostsRequest


AnalysisRequest = Annotated[
    Union[CoffeeAnalysisRequest, RestaurantAnalysisRequest, GymAnalysisRequest, BeautyAnalysisRequest],
    Field(discriminator="sector"),
]
ANALYSIS_REQUEST_ADAPTER = TypeAdapter(AnalysisRequest)


class ProductCode(StrEnum):
    LOCATION_REPORT_V1 = "location_report_v1"


class OrderState(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    FULFILLMENT_IN_PROGRESS = "fulfillment_in_progress"
    FULFILLED = "fulfilled"
    ATTENTION_REQUIRED = "attention_required"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class PaymentState(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    REFUND_FAILED = "refund_failed"


class FulfillmentState(StrEnum):
    NOT_STARTED = "not_started"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYSIS_RUNNING = "analysis_running"
    REPORT_PENDING = "report_pending"
    DELIVERY_PENDING = "delivery_pending"
    COMPLETED = "completed"
    NOT_SCORE_READY = "not_score_ready"
    ANALYSIS_FAILED = "analysis_failed"
    ANALYSIS_TIMED_OUT = "analysis_timed_out"
    REPORT_FAILED = "report_failed"
    DELIVERY_FAILED = "delivery_failed"


class OrderCreateRequest(StrictRequestModel):
    product_code: Literal[ProductCode.LOCATION_REPORT_V1]
    customer_email: NonEmptyString
    analysis_request: AnalysisRequest

    @field_validator("customer_email")
    @classmethod
    def validate_customer_email(cls, value: str) -> str:
        local, sep, domain = value.rpartition("@")
        if not sep or not local or not domain or "." not in domain or any(ch.isspace() for ch in value):
            raise ValueError("customer_email must be a valid email address")
        return f"{local}@{domain.lower()}"

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class OrderCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v1"] = "v1"
    request_id: UUID
    order_id: UUID
    product_code: Literal[ProductCode.LOCATION_REPORT_V1]
    order_state: Literal[OrderState.PENDING_PAYMENT]
    payment_state: Literal[PaymentState.PENDING]
    fulfillment_state: Literal[FulfillmentState.NOT_STARTED]
    checkout_url: str
    checkout_expires_at: str | None = None
