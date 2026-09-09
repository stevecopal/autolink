from dataclasses import dataclass


class ProviderError(Exception):
    """Base error raised by a payment provider adapter."""


class ProviderUnavailable(ProviderError):
    """Provider credentials or network service are unavailable."""


@dataclass(frozen=True)
class PaymentInitialization:
    transaction_id: str
    checkout_url: str = ""


class PaymentProvider:
    name = ""

    def initialize(self, payment):
        raise ProviderUnavailable(f"Provider {self.name} is not configured")

    def verify_webhook(self, request):
        return True


class PayUnitProvider(PaymentProvider):
    name = "PAYUNIT"


class CamPayProvider(PaymentProvider):
    name = "CAMPAY"


PROVIDERS = {
    "PAYUNIT": PayUnitProvider(),
    "CAMPAY": CamPayProvider(),
}


def get_provider(name):
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        raise ProviderError(f"Unsupported provider: {name}") from exc
