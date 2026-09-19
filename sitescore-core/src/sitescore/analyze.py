from sitescore.config.sectors import Sector
from sitescore.engines.confidence import calculate_confidence
from sitescore.engines.decision import calculate_decision
from sitescore.engines.financial import calculate_financial_metrics
from sitescore.engines.location import calculate_location_score
from sitescore.engines.revenue import calculate_revenue
from sitescore.fingerprint import generate_analysis_fingerprint
from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.canonical import CanonicalAnalysisResult
from sitescore.schemas.metadata import current_model_versions
from sitescore.schemas.revenue_inputs import (
    BeautyRevenueInput,
    CoffeeRevenueInput,
    GymRevenueInput,
    RestaurantRevenueInput,
)


def _get_unit_price(data: AnalysisInput) -> float:
    """
    Financial Engine'in break-even volume hesabında
    kullanacağı sektör-spesifik birim fiyatı döndürür.

    Coffee:
        Average ticket / transaction

    Restaurant:
        Average ticket / cover

    Gym:
        Monthly membership fee / active member

    Beauty:
        Average ticket / appointment
    """

    revenue_input = data.revenue_input

    if data.sector == Sector.COFFEE:
        if not isinstance(
            revenue_input,
            CoffeeRevenueInput,
        ):
            raise TypeError(
                "Coffee sector requires CoffeeRevenueInput"
            )

        return revenue_input.average_ticket

    if data.sector == Sector.RESTAURANT:
        if not isinstance(
            revenue_input,
            RestaurantRevenueInput,
        ):
            raise TypeError(
                "Restaurant sector requires "
                "RestaurantRevenueInput"
            )

        return revenue_input.average_ticket

    if data.sector == Sector.GYM:
        if not isinstance(
            revenue_input,
            GymRevenueInput,
        ):
            raise TypeError(
                "Gym sector requires GymRevenueInput"
            )

        return revenue_input.monthly_membership_fee

    if data.sector == Sector.BEAUTY:
        if not isinstance(
            revenue_input,
            BeautyRevenueInput,
        ):
            raise TypeError(
                "Beauty sector requires BeautyRevenueInput"
            )

        return revenue_input.average_ticket

    raise ValueError(
        f"Unsupported sector: {data.sector}"
    )


def analyze(
    data: AnalysisInput,
) -> CanonicalAnalysisResult:
    """
    SiteScore V1 canonical analysis orchestrator.

    Business logic burada yeniden uygulanmaz.

    Sıra:

        Revenue Engine
            ↓
        Location Engine
            ↓
        Financial Engine
            ↓
        Decision Engine
            ↓
        Confidence Engine
            ↓
        Model Metadata
            ↓
        Deterministic Fingerprint
            ↓
        CanonicalAnalysisResult

    Aynı input + aynı model sürümleri
    deterministik olarak aynı sonucu üretmelidir.
    """

    # -------------------------------------------------
    # 1. Revenue Engine
    # -------------------------------------------------

    revenue = calculate_revenue(
        sector=data.sector,
        data=data.revenue_input,
    )

    # -------------------------------------------------
    # 2. Location Engine
    # -------------------------------------------------

    location = calculate_location_score(
        sector=data.sector,
        scores=data.category_scores,
    )

    # -------------------------------------------------
    # 3. Financial Engine
    # -------------------------------------------------

    financial = calculate_financial_metrics(
        sector=data.sector,
        revenue=revenue,
        rent=data.monthly_rent,
        fixed_labor=data.fixed_labor,
        fixed_overhead=data.fixed_overhead,
        unit_price=_get_unit_price(data),
    )

    # -------------------------------------------------
    # 4. Decision Engine
    # -------------------------------------------------

    decision = calculate_decision(
        location=location,
        financial=financial,
    )

    # -------------------------------------------------
    # 5. Confidence Engine
    # -------------------------------------------------

    confidence = calculate_confidence(
        sector=data.sector,
        geographic_level=data.geographic_level.value,
        data_age_years=data.data_age_years,
        coverage={
            key: value.value
            for key, value in data.data_coverage.items()
        },
        input_qualities={
            key: value.value
            for key, value in data.input_qualities.items()
        },
    )

    # -------------------------------------------------
    # 6. Model Versions
    # -------------------------------------------------

    versions = current_model_versions()

    # -------------------------------------------------
    # 7. Deterministic Analysis Fingerprint
    # -------------------------------------------------

    fingerprint = generate_analysis_fingerprint(
        data=data,
        versions=versions,
    )

    # -------------------------------------------------
    # 8. Canonical Output
    # -------------------------------------------------

    return CanonicalAnalysisResult(
        analysis_fingerprint=fingerprint,
        model_versions=versions,
        location=location,
        financial=financial,
        decision=decision,
        confidence=confidence,
    )