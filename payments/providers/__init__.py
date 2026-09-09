from .base import (
    ProviderError,
    ProviderUnavailable,
    PaymentInitialization,
    PayUnitProvider,
    payunit_provider,
)


def get_provider(name="PAYUNIT"):
    """Return the payment provider. Only PayUnit is supported."""
    if name.upper() != "PAYUNIT":
        raise ProviderError(f"Unsupported provider: {name}. Only PAYUNIT is available.")
    return payunit_provider


__all__ = [
    "ProviderError",
    "ProviderUnavailable",
    "PaymentInitialization",
    "PayUnitProvider",
    "payunit_provider",
    "get_provider",
]
