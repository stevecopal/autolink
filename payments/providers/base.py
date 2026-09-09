"""
PayUnit payment provider — single provider for AutoLink.

Environment variables (in .env):
  PAYUNIT_API_KEY       – Application token (x-api-key header)
  PAYUNIT_API_USER      – API username (Basic auth)
  PAYUNIT_API_PASSWORD  – API password (Basic auth)
  PAYUNIT_API_URL       – Base URL, default https://gateway.payunit.net
  PAYUNIT_MODE          – "live" or "test"
  PAYMENT_WEBHOOK_SECRET – Shared secret for webhook signature verification
  SITE_URL              – Public site URL for callbacks (https://...)
"""

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger("payments")


class ProviderError(Exception):
    """Base error raised by a payment provider adapter."""


class ProviderUnavailable(ProviderError):
    """Provider credentials or network service are unavailable."""


@dataclass(frozen=True)
class PaymentInitialization:
    transaction_id: str
    checkout_url: str = ""


class PayUnitProvider:
    """
    PayUnit REST API integration.
    Docs: https://developer.payunit.net/rest-api/initialize-payment
    """

    name = "PAYUNIT"

    # ── credentials ──────────────────────────────────────────────

    def _base_url(self):
        url = getattr(settings, "PAYUNIT_API_URL", "") or "https://gateway.payunit.net"
        return url.rstrip("/")

    def _api_key(self):
        key = getattr(settings, "PAYUNIT_API_KEY", "")
        if not key:
            raise ProviderUnavailable("PAYUNIT_API_KEY is not configured in .env")
        return key

    def _api_user(self):
        user = getattr(settings, "PAYUNIT_API_USER", "")
        if not user:
            raise ProviderUnavailable("PAYUNIT_API_USER is not configured in .env")
        return user

    def _api_password(self):
        pw = getattr(settings, "PAYUNIT_API_PASSWORD", "")
        if not pw:
            raise ProviderUnavailable("PAYUNIT_API_PASSWORD is not configured in .env")
        return pw

    def _mode(self):
        return getattr(settings, "PAYUNIT_MODE", "test")

    def _headers(self):
        credentials = base64.b64encode(
            f"{self._api_user()}:{self._api_password()}".encode()
        ).decode()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
            "x-api-key": self._api_key(),
            "mode": self._mode(),
        }

    def _site_url(self):
        return getattr(settings, "SITE_URL", "http://localhost:8000")

    # ── initialize ───────────────────────────────────────────────

    def initialize(self, payment):
        """
        Step 1 – Initialize a payment on PayUnit.
        POST {BASE_URL}/api/gateway/initialize

        Returns a PaymentInitialization with the PayUnit transaction_id
        and the hosted checkout URL the user should be redirected to.
        """
        try:
            payload = {
                "total_amount": int(payment.amount),
                "currency": payment.currency,
                "transaction_id": payment.idempotency_key,
                "return_url": f"{self._site_url()}/paiement/{payment.pk}/",
                "notify_url": f"{self._site_url()}/webhook/",
                "payment_country": "CM",
            }

            resp = requests.post(
                f"{self._base_url()}/api/gateway/initialize",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()

            if body.get("status") != "SUCCESS":
                msg = body.get("message", "PayUnit initialize failed")
                logger.error("PayUnit initialize error: %s", msg)
                raise ProviderUnavailable(msg)

            data = body.get("data", {})
            transaction_id = data.get("transaction_id", "")
            checkout_url = data.get("transaction_url", "")

            if not transaction_id:
                raise ProviderUnavailable("PayUnit returned no transaction_id")

            return PaymentInitialization(
                transaction_id=transaction_id,
                checkout_url=checkout_url,
            )

        except requests.exceptions.ConnectionError:
            raise ProviderUnavailable("Cannot connect to PayUnit API")
        except requests.exceptions.Timeout:
            raise ProviderUnavailable("PayUnit API timed out")
        except requests.exceptions.HTTPError as exc:
            logger.error("PayUnit HTTP %s", exc)
            status = exc.response.status_code if exc.response else "?"
            raise ProviderUnavailable(f"PayUnit API error {status}")
        except (KeyError, ValueError, TypeError) as exc:
            logger.error("PayUnit response parse error: %s", exc)
            raise ProviderUnavailable("Invalid PayUnit response")

    # ── make payment (collect money) ─────────────────────────────

    def make_payment(self, payment, phone_number, gateway="CM_ORANGE"):
        """
        Step 2 – Confirm / collect the payment.
        POST {BASE_URL}/api/gateway/makepayment

        After initialize() the user is redirected to the hosted page,
        OR you can call this endpoint directly with the phone number
        to trigger the USSD push on the user's phone.

        Returns the provider_transaction_id on success.
        """
        try:
            payload = {
                "gateway": gateway,
                "amount": int(payment.amount),
                "transaction_id": payment.idempotency_key,
                "phone_number": phone_number,
                "currency": payment.currency,
                "paymentType": "button",
                "return_url": f"{self._site_url()}/paiement/{payment.pk}/",
                "notify_url": f"{self._site_url()}/webhook/",
            }

            resp = requests.post(
                f"{self._base_url()}/api/gateway/makepayment",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()

            if body.get("status") != "SUCCESS":
                msg = body.get("message", "PayUnit makepayment failed")
                logger.error("PayUnit makepayment error: %s", msg)
                raise ProviderUnavailable(msg)

            data = body.get("data", {})
            return data.get("provider_transaction_id") or data.get("transaction_id", "")

        except requests.exceptions.ConnectionError:
            raise ProviderUnavailable("Cannot connect to PayUnit API")
        except requests.exceptions.Timeout:
            raise ProviderUnavailable("PayUnit API timed out")
        except requests.exceptions.HTTPError as exc:
            logger.error("PayUnit HTTP %s", exc)
            status = exc.response.status_code if exc.response else "?"
            raise ProviderUnavailable(f"PayUnit API error {status}")

    # ── get status ───────────────────────────────────────────────

    def get_transaction_status(self, transaction_id):
        """
        GET {BASE_URL}/api/gateway/status/{transaction_id}

        Returns dict with transaction_status (SUCCESS/FAILED/CANCELLED/PENDING).
        """
        try:
            resp = requests.get(
                f"{self._base_url()}/api/gateway/status/{transaction_id}",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            body = resp.json()
            return body.get("data", {})
        except Exception as exc:
            logger.error("PayUnit status check error: %s", exc)
            return {}

    # ── webhook verification ─────────────────────────────────────

    def verify_webhook(self, request):
        """
        Verify PayUnit webhook authenticity.

        PayUnit sends a POST to notify_url with this body:
        {
          "status": "SUCCESS",
          "data": {
            "transaction_status": "SUCCESS|FAILED|CANCELLED",
            "transaction_id": "PU ...",
            "transaction_amount": 10000,
            "transaction_currency": "XAF",
            ...
          }
        }

        We verify by checking the shared PAYMENT_WEBHOOK_SECRET.
        If no secret is configured, we accept all webhooks (dev mode).
        """
        try:
            secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")
            if not secret:
                return True

            # PayUnit may send signature in X-PayUnit-Signature or X-Webhook-Secret
            signature = (
                request.headers.get("X-PayUnit-Signature", "")
                or request.headers.get("X-Webhook-Signature", "")
            )

            if not signature:
                # Some PayUnit setups use HMAC on the raw body
                raw = request.body
                expected = hmac.new(
                    secret.encode("utf-8"), raw, hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(signature, expected)

            # If we have a signature header, compare directly
            raw = request.body
            expected = hmac.new(
                secret.encode("utf-8"), raw, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)

        except Exception as exc:
            logger.error("Webhook verification error: %s", exc)
            return False

    # ── parse webhook payload ────────────────────────────────────

    @staticmethod
    def parse_webhook(payload):
        """
        Normalize the PayUnit webhook payload into a standard dict:
        {
          "transaction_id": "...",
          "status": "SUCCESS|FAILED|CANCELLED",
          "amount": 1000,
          "currency": "XAF",
          "provider_reference": "...",
          "metadata": {},
        }
        """
        data = payload.get("data", payload)

        status_raw = data.get("transaction_status", payload.get("status", "")).upper()
        status_map = {
            "SUCCESS": "SUCCESS",
            "FAILED": "FAILED",
            "CANCELLED": "CANCELLED",
            "PENDING": "PENDING",
        }
        status = status_map.get(status_raw, status_raw)

        return {
            "transaction_id": data.get("transaction_id", ""),
            "status": status,
            "amount": data.get("transaction_amount", payload.get("amount")),
            "currency": data.get("transaction_currency", payload.get("currency", "XAF")),
            "provider_reference": data.get("transaction_gateway", ""),
            "message": data.get("message", data.get("message", "")),
        }


# Singleton
payunit_provider = PayUnitProvider()
