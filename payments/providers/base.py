"""
CamPay payment provider — single provider for AutoLink.

Environment variables (in .env or .env.example):
  CAMPAY_ENVIRONMENT     – DEV or PROD (default DEV)
  CAMPAY_APP_USERNAME    – App username
  CAMPAY_APP_PASSWORD    – App password
  CAMPAY_WEBHOOK_SECRET  – Secret used to validate webhooks (HMAC)
  CAMPAY_BASE_URL        – optional override for the base API URL

Docs flow used here:
  1. POST {BASE_URL}/token/  -> token
  2. POST {BASE_URL}/collect/ -> create payment (PENDING)
  3. Webhook -> status update (SUCCESS/FAILED)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger("payments")


class CamPayError(Exception):
    """Base error raised by the CamPay adapter."""


class CamPayUnavailable(CamPayError):
    """Credentials, network or API are unavailable."""


@dataclass(frozen=True)
class CamPayCollectResult:
    """Result of a CamPay collect (init) call."""

    success: bool
    # CamPay's external_reference is our local transaction id (mirror).
    external_reference: str
    # Optional raw provider id / message if useful for logs/support.
    provider_id: Optional[str] = None
    message: Optional[str] = None


class CamPayProvider:
    name = "CAMPAY"

    # ── environment ────────────────────────────────────────────────────

    def _environment(self) -> str:
        env = getattr(settings, "CAMPAY_ENVIRONMENT", "DEV") or "DEV"
        env = env.strip().upper()
        if env not in {"DEV", "PROD"}:
            raise CamPayUnavailable("CAMPAY_ENVIRONMENT must be DEV or PROD")
        return env

    def _base_url(self) -> str:
        override = getattr(settings, "CAMPAY_BASE_URL", "") or ""
        if override:
            return override.rstrip("/")
        return (
            "https://demo.campay.net/api"
            if self._environment() == "DEV"
            else "https://www.campay.net/api"
        )

    def _username(self) -> str:
        u = getattr(settings, "CAMPAY_APP_USERNAME", "") or ""
        if not u:
            raise CamPayUnavailable("CAMPAY_APP_USERNAME is not configured in .env")
        return u

    def _password(self) -> str:
        p = getattr(settings, "CAMPAY_APP_PASSWORD", "") or ""
        if not p:
            raise CamPayUnavailable("CAMPAY_APP_PASSWORD is not configured in .env")
        return p

    def _webhook_secret(self) -> str:
        return getattr(settings, "CAMPAY_WEBHOOK_SECRET", "") or ""

    # ── authentication ──────────────────────────────────────────────────

    def get_token(self) -> str:
        """
        Retourne un token temporaire CamPay.
        POST {BASE_URL}/token/
        {"username": "...", "password": "..."}
        """
        try:
            payload = {"username": self._username(), "password": self._password()}

            resp = requests.post(
                f"{self._base_url()}/token/",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            try:
                body = resp.json()
            except ValueError:
                logger.error(
                    "CAMPAY TOKEN | invalid_json status=%s response=%s",
                    resp.status_code,
                    resp.text,
                )
                raise CamPayUnavailable("Réponse CamPay invalide (token)")

            if resp.status_code != 200:
                logger.error(
                    "CAMPAY TOKEN | non_200 status=%s response=%s",
                    resp.status_code,
                    resp.text,
                )
                if resp.status_code in (401, 403):
                    raise CamPayUnavailable("Credentials CamPay invalides")
                if resp.status_code == 404:
                    raise CamPayUnavailable("Endpoint CamPay /token/ introuvable")
                raise CamPayUnavailable(
                    f"Erreur API CamPay (HTTP {resp.status_code})"
                )

            if not isinstance(body, dict):
                logger.error("CAMPAY TOKEN | invalid_response_shape=%s", body)
                raise CamPayUnavailable("Réponse CamPay invattendue pour le token")

            token = (
                body.get("token")
                or body.get("access_token")
                or body.get("token_key")
                or ""
            )
            if not token:
                logger.error("CAMPAY TOKEN | missing_token response=%s", body)
                raise CamPayUnavailable("CamPay n'a pas retourné de token")
            return str(token)

        except CamPayError:
            # Erreur métier CamPay déjà explicite : on la propage telle quelle.
            raise
        except Exception as e:
            # Toute autre erreur (réseau, config, bug interne) est loguée
            # avec la trace complète puis convertie en erreur gérable.
            logger.exception("Erreur CamPay : %s", e)
            raise CamPayError(str(e)) from e

    # ── collect (init) ─────────────────────────────────────────────────

    def collect(self, payment, phone_number: str) -> CamPayCollectResult:
        """
        Étape 1 : initialisation du paiement CamPay (collect).
        POST {BASE_URL}/collect/

        Payload strict attendu par CamPay (valeurs = chaînes de caractères) :
          {
            "amount": "1000",
            "currency": "XAF",
            "from": "237XXXXXXXXX",
            "description": "Activation garage Autolink",
            "external_reference": "<str(payment.id)>"
          }

        Headers:
          Authorization: Token <token>   (token obtenu via POST /token/)
          Content-Type: application/json

        Si HTTP 200, on considère que la transaction est créée et on passe
        le Payment en PENDING côté notre base.
        """
        token = self.get_token()
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
        }

        clean_phone = self._normalize_phone(phone_number)

        external_reference = str(payment.id)
        # Payload strict : toutes les valeurs sont des chaînes de caractères.
        payload = {
            "amount": "1000",
            "currency": "XAF",
            "from": clean_phone,
            "description": "Activation garage Autolink",
            "external_reference": external_reference,
        }

        logger.info(
            "CAMPAY COLLECT | internal_id=%s | phone=%s",
            external_reference,
            clean_phone,
        )
        logger.debug("CAMPAY COLLECT | request_payload=%s", payload)

        try:
            resp = requests.post(
                f"{self._base_url()}/collect/",
                json=payload,
                headers=headers,
                timeout=30,
            )

            try:
                body = resp.json()
            except ValueError:
                logger.error(
                    "CAMPAY COLLECT | invalid_json status=%s response=%s",
                    resp.status_code,
                    resp.text,
                )
                raise CamPayUnavailable("Réponse CamPay invalide (collect)")

            logger.debug(
                "CAMPAY COLLECT | status=%s response=%s",
                resp.status_code,
                resp.text,
            )

            if resp.status_code != 200:
                msg = body.get("message") if isinstance(body, dict) else None
                error_msg = body.get("error") if isinstance(body, dict) else None
                logger.error(
                    "CAMPAY COLLECT | non_200 status=%s response=%s message=%s error=%s",
                    resp.status_code,
                    resp.text,
                    msg,
                    error_msg,
                )
                if resp.status_code in (401, 403):
                    raise CamPayUnavailable("Credentials CamPay invalides")
                if resp.status_code == 404:
                    raise CamPayUnavailable("Endpoint CamPay /collect/ introuvable")
                if resp.status_code == 422:
                    raise CamPayUnavailable(
                        f"Payload CamPay invalide : {msg or error_msg or resp.text}"
                    )
                if resp.status_code == 429:
                    raise CamPayUnavailable("CamPay rate limit atteint")
                raise CamPayUnavailable(
                    f"Erreur API CamPay (HTTP {resp.status_code})"
                )

            if not isinstance(body, dict):
                logger.error("CAMPAY COLLECT | invalid_response_shape=%s", body)
                raise CamPayUnavailable("Réponse CamPay invattendue")

            provider_id = (
                body.get("id")
                or body.get("transaction_id")
                or body.get("external_reference")
                or ""
            )

            return CamPayCollectResult(
                success=True,
                external_reference=external_reference,
                provider_id=provider_id or None,
                message=body.get("message") or body.get("status") or None,
            )

        except CamPayError:
            # Erreur métier CamPay déjà explicite : on la propage telle quelle.
            raise
        except Exception as e:
            # Toute autre erreur (réseau, payload, bug interne) est loguée
            # avec la trace complète puis convertie en erreur gérable.
            logger.exception("Erreur CamPay : %s", e)
            raise CamPayError(str(e)) from e

    # ── webhook ────────────────────────────────────────────────────────

    def verify_webhook_signature(self, request) -> bool:
        """
        Vérifie la signature du webhook CamPay via HMAC.
        Compatible avec les payloads JSON bruts.
        En mode dev (secret vide), on accepte le webhook.
        """
        secret = self._webhook_secret()
        if not secret:
            logger.warning(
                "CAMPAY_WEBHOOK_SECRET non configuré. Validation du webhook ignorée (mode développement)."
            )
            return True

        # Plusieurs conventions d'en-tête sont possibles selon la config CamPay.
        signature = (
            request.META.get("HTTP_X_CAMPAY_SIGNATURE")
            or request.META.get("HTTP_X_WEBHOOK_SIGNATURE")
            or request.META.get("HTTP_X_PAYMENT_WEBHOOK_SECRET")
            or request.META.get("HTTP_X_WEBHOOK_SECRET")
            or request.headers.get("X-Campay-Signature")
            or request.headers.get("X-Webhook-Signature")
            or request.headers.get("X-Payment-Webhook-Secret")
            or request.headers.get("X-Webhook-Secret")
        )

        if not signature:
            logger.error("CAMPAY WEBHOOK | aucune signature trouvée")
            return False

        try:
            raw_body = request.body
            expected_signature = hmac.new(
                secret.encode("utf-8"), raw_body, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error("CAMPAY WEBHOOK | erreur vérification signature=%s", e)
            return False

    def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise le payload webhook CamPay en un dictionnaire standardisé.

        Champs attendus (adaptés à la doc fournie) :
          - external_reference : notre transaction locale
          - status : SUCCESSFUL / FAILED (ou équivalent)
          - amount, currency, phone_number, message, etc.
        """
        if not isinstance(payload, dict):
            return {}

        # Le webhook peut placer les données à la racine ou dans un bloc "data".
        data = payload.get("data") or payload

        status_raw = (
            data.get("status")
            or payload.get("status")
            or data.get("payment_status")
            or payload.get("payment_status")
            or ""
        )

        status_map = {
            "SUCCESSFUL": "SUCCESS",
            "SUCCESS": "SUCCESS",
            "FAILED": "FAILED",
            "FAIL": "FAILED",
            "CANCELLED": "CANCELLED",
            "PENDING": "PENDING",
        }
        status = status_map.get(str(status_raw).upper(), str(status_raw).upper())

        external_reference = (
            data.get("external_reference") or payload.get("external_reference") or ""
        )

        return {
            "external_reference": external_reference,
            "transaction_id": external_reference,  # compatibilité avec process_webhook existant
            "status": status,
            "amount": data.get("amount") or payload.get("amount"),
            "currency": data.get("currency") or payload.get("currency") or "XAF",
            "provider_reference": data.get("id")
            or data.get("transaction_id")
            or payload.get("transaction_id")
            or "",
            "message": data.get("message") or payload.get("message") or "",
            "phone_number": data.get("from")
            or data.get("phone_number")
            or payload.get("phone_number")
            or "",
            "raw_payload": payload,
        }

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """
        Accepte +237XXXXXXXXX, 237XXXXXXXXX ou 9 chiffres.
        Retourne 237XXXXXXXXX (12 caractères) comme semble l'attendre CamPay.
        """
        raw = phone.replace(" ", "").replace("-", "").replace(".", "")
        if raw.startswith("+237"):
            raw = raw[4:]
        elif raw.startswith("237") and len(raw) > 9:
            raw = raw[3:]
        if not raw.isdigit() or len(raw) != 9:
            raise CamPayUnavailable("Numéro de téléphone invalide")
        return "237" + raw


# Singleton
_cam_pay_provider = CamPayProvider()
