"""Execution-layer provider exceptions; these are not domain evidence states."""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for provider execution/policy failures."""


class ProviderUnavailableError(ProviderError):
    pass


class ProviderRateLimitError(ProviderUnavailableError):
    pass


class ProviderQuotaError(ProviderUnavailableError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderMalformedResponseError(ProviderError):
    pass


class ProviderInvariantError(ProviderError):
    pass


class ProviderPolicyError(ProviderError):
    pass
