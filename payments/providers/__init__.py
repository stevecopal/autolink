from .base import (
    CamPayCollectResult,
    CamPayProvider,
    CamPayError,
    CampayProvider,
    PaymentInitialization,
    ProviderError,
    ProviderUnavailable,
)


def provider_unavailable(error: str) -> Exception:
    return CamPayError(error)


# Lazy provider accessor. Only CamPay is supported.
def get_provider(name: str = "CAMPAY") -> CamPayProvider:
    if name.upper() not in {"CAMPAY", "CAMPAY_NET"}:
        raise CamPayError(f"Unsupported provider: {name}. Only CAMPAY is available.")
    return _get_cam_pay_provider()


_cam_pay_singleton: CamPayProvider | None = None


def _get_cam_pay_provider() -> CamPayProvider:
    global _cam_pay_singleton
    if _cam_pay_singleton is None:
        _cam_pay_singleton = CamPayProvider()
    return _cam_pay_singleton


def set_cam_pay_provider_for_tests(provider: CamPayProvider) -> None:
    global _cam_pay_singleton
    _cam_pay_singleton = provider


__all__ = [
    "CamPayProvider",
    "CamPayError",
    "CamPayCollectResult",
    "provider_unavailable",
    "get_provider",
    "set_cam_pay_provider_for_tests",
]
