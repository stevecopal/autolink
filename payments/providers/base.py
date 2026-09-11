# payments/providers/campay.py
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger("payments")


class ProviderError(Exception):
    """Erreur de base levée par un fournisseur de paiement."""

    pass


class ProviderUnavailable(ProviderError):
    """Le fournisseur est indisponible (clés ou réseau)."""

    pass


@dataclass(frozen=True)
class PaymentInitialization:
    transaction_id: str
    checkout_url: str = ""


class CampayProvider:
    name = "CAMPAY"

    def __init__(self):
        self._cached_token = None

    def _base_url(self):
        env = getattr(settings, "CAMPAY_ENVIRONMENT", "DEV")
        return (
            "https://www.campay.net/api" if env == "PROD" else "https://demo.campay.net/api"
        )

    def _auth(self):
        username = getattr(settings, "CAMPAY_APP_USERNAME", "")
        password = getattr(settings, "CAMPAY_APP_PASSWORD", "")
        if not username or not password:
            raise ProviderUnavailable(
                "CAMPAY_APP_USERNAME ou CAMPAY_APP_PASSWORD non configurés."
            )
        return username, password

    def get_token(self, force=False):
        """
        Obtenir (et mettre en cache) le jeton d'accès Campay.
        POST {BASE_URL}/token/  →  Authorization: Token <token>
        """
        if not force and self._cached_token:
            return self._cached_token

        username, password = self._auth()
        url = f"{self._base_url()}/token/"
        try:
            resp = requests.post(
                url,
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Campay Token Error: {e}")
            raise ProviderUnavailable(f"Erreur réseau Campay: {e}")

        token = body.get("token") or body.get("access")
        if not token:
            logger.error(f"Campay Token refusé: {body}")
            raise ProviderUnavailable(
                f"Authentification Campay refusée: {body}"
            )
        self._cached_token = token
        return token

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.get_token()}",
            "Accept": "application/json",
        }

    def _post(self, path, payload, timeout=30):
        url = f"{self._base_url()}{path}"
        logger.debug(f"Campay Request: {url} | Payload: {json.dumps(payload, indent=2)}")
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=timeout)
            if resp.status_code == 401:
                # Jeton expiré ou invalide : régénérer puis réessayer une seule fois.
                logger.warning("Campay 401: renouvellement du jeton puis nouvel essai.")
                self._cached_token = None
                resp = requests.post(
                    url, json=payload, headers=self._headers(), timeout=timeout
                )

            if resp.status_code >= 400:
                # Capturer le message d'erreur renvoyé par Campay (JSON) pour
                # pouvoir diagnostiquer le refus (ex: numéro invalide, montant…).
                detail = ""
                try:
                    err = resp.json()
                    detail = err.get("message") or err.get("detail") or err.get("error") or ""
                except ValueError:
                    err = None
                if detail:
                    logger.error(
                        "Campay Error %s %s: %s (Payload: %s)",
                        resp.status_code, url, detail, payload,
                    )
                    raise ProviderUnavailable(f"Erreur Campay (%s): %s" % (resp.status_code, detail))
                logger.error(f"Campay Request Error {url}: HTTP {resp.status_code} {resp.text}")
                raise ProviderUnavailable(
                    f"Erreur réseau Campay: HTTP {resp.status_code} {resp.reason}"
                )

            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Campay Request Error {url}: {e}")
            raise ProviderUnavailable(f"Erreur réseau Campay: {e}")

    @staticmethod
    def _check_body_error(body, payload):
        status = (body.get("status") or "").lower()
        if status and status not in ("success", "successful", "ok"):
            error_msg = body.get("message") or body.get("detail") or "Erreur Campay inconnue"
            logger.error(
                f"Campay Error: {error_msg} (Payload: {json.dumps(payload, indent=2)})"
            )
            raise ProviderUnavailable(f"Erreur Campay: {error_msg}")

    @staticmethod
    def _as_amount(amount):
        try:
            value = int(Decimal(str(amount)))
        except (InvalidOperation, ValueError, TypeError):
            raise ProviderUnavailable("Montant invalide.")
        if value <= 0:
            raise ProviderUnavailable("Le montant doit être supérieur à 0.")
        # Le sandbox Campay (DEV) plafonne à 25 XAF (erreur ER201 sinon).
        if settings.CAMPAY_ENVIRONMENT == "DEV" and value > 25:
            raise ProviderUnavailable(
                f"En mode DEV, le montant max est 25 XAF. Reçu: {value} XAF."
            )
        return value

    def _site_url(self):
        return getattr(settings, "SITE_URL", "http://localhost:8000")

    def initialize(self, payment):
        """
        Étape 1 (INITIALIZE) : valide le paiement et les identifiants Campay.
        N'appelle PAS /collect/ (il n'y a pas encore de numéro de téléphone) :
        les opérateurs disponibles (ORANGE_CM / MTN_CM) sont renvoyés par la vue,
        puis le vrai collect a lieu dans make_payment() lors du choix de l'opérateur.
        Le token Campay est sollicité ici pour vérifier la connexion/l'accès API.
        """
        if not payment.amount:
            raise ProviderUnavailable("Montant manquant.")
        if not payment.currency:
            raise ProviderUnavailable("Devise manquante.")
        if not payment.idempotency_key:
            raise ProviderUnavailable("Clé d'idempotence manquante.")

        self._as_amount(payment.amount)
        # Vérifie l'authentification (lévera ProviderUnavailable si invalide).
        self.get_token()

        return PaymentInitialization(
            transaction_id=payment.idempotency_key,
            checkout_url=(
                f"{self._site_url()}/paiement/{payment.pk}/?provider={payment.provider}"
            ),
        )

    def make_payment(self, payment, phone_number, gateway="ORANGE_CM"):
        """
        Étape 2 (MAKE PAYMENT) : déclencher le collect USSD sur Campay.
        POST {BASE_URL}/collect/  (fields documentés de l'API Campay)
        Retourne la référence transactionnelle Campay (provider_transaction_id).
        """
        if not payment.idempotency_key:
            raise ProviderUnavailable("Clé d'idempotence manquante.")

        # L'API Campay attend le champ "from" SANS le signe '+' en tête :
        # "2376XXXXXXXX" (indicatif pays 237 inclus). Un numéro "+2376…"
        # est rejeté par /collect/ avec une erreur HTTP 400 Bad Request.
        normalized_phone = str(phone_number or "").replace(" ", "").lstrip("+")
        if not normalized_phone.startswith("237"):
            normalized_phone = "237" + normalized_phone.lstrip("0")

        amount = self._as_amount(payment.amount)
        payload = {
            # Campay attend le montant en FCFA (entier, pas en centimes).
            "amount": amount,
            "currency": payment.currency,
            "from": normalized_phone,  # "2376XXXXXXXX" (indicatif pays, sans '+')
            "description": "Activation de votre garage sur AutoLink",
            "external_reference": payment.idempotency_key,  # Référence métier unique
        }

        body = self._post("/collect/", payload)
        self._check_body_error(body, payload)

        return body.get("transaction_id") or body.get("reference") or payment.idempotency_key

    def collect(self, payment, phone_number, gateway="ORANGE_CM"):
        """
        Collect CamPay (rétrocompatibilité) : effectue un paiement mobile money.
        Retourne le résultat de la transaction.
        """
        transaction_id = self.make_payment(
            payment, phone_number, gateway=gateway
        )
        return PaymentInitialization(
            transaction_id=transaction_id,
        )

    def verify_webhook(self, request):
        """
        Vérifier la signature du webhook Campay.
        """
        try:
            secret = getattr(settings, "CAMPAY_WEBHOOK_SECRET", "")
            if not secret:
                logger.warning(
                    "CAMPAY_WEBHOOK_SECRET non configuré. Mode développement."
                )
                return True

            signature = request.headers.get("X-CamPay-Signature")
            if not signature:
                logger.error("Signature webhook manquante.")
                return False

            raw_body = request.body
            expected_signature = hmac.new(
                secret.encode(), raw_body, hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Erreur vérification webhook: {e}")
            return False

    def parse_webhook(self, payload):
        """
        Parser le payload du webhook Campay.
        """
        status_raw = payload.get("status", "").lower()
        status_map = {
            "success": "SUCCESS",
            "successful": "SUCCESS",
            "failed": "FAILED",
            "cancelled": "CANCELLED",
            "pending": "PENDING",
        }
        return {
            "transaction_id": payload.get("transaction_id", ""),
            # CamPay renvoie external_reference = idempotency_key du paiement.
            "external_reference": payload.get("external_reference", ""),
            # Référence CamPay (prestation) utilisée comme provider_reference.
            "provider_reference": payload.get("reference", ""),
            "status": status_map.get(status_raw, status_raw),
            "amount": payload.get("amount"),
            "currency": payload.get("currency", "XAF"),
            "provider": payload.get("provider", ""),
            "phone_number": payload.get("phone_number", ""),
        }


campay_provider = CampayProvider()

# ── Compatibility aliases ──────────────────────────────────────────────────────
# These aliases let __init__.py, views.py, and tests.py import the names they
# expect while base.py keeps the original CamPay naming.
CamPayProvider = CampayProvider
CamPayCollectResult = PaymentInitialization
CamPayError = ProviderError
