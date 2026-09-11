from decimal import Decimal

from decouple import config


GARAGE_ACTIVATION_CURRENCY = "XAF"  # Devise (FCFA)

CAMPAY_ENVIRONMENT = config("CAMPAY_ENVIRONMENT", default="DEV")

# Campay impose des bornes par opérateur sur /api/collect/ :
#   - MTN    : montant minimum 2 XAF
#   - Orange : montant minimum 10 XAF
# En sandbox (DEV, https://demo.campay.net), le montant est plafonné à 25 XAF
# (erreur "ER201 ... Maximum amount is 25.00 XAF" au-delà).
# L'activation d'un garage coûte donc :
#   - DEV  : 20 XAF (entre la borne Orange min 10 et le plafond sandbox 25)
#   - PROD : 1000 XAF (vraie tarification, montrant "1 000 FCFA" dans l'UI)
GARAGE_ACTIVATION_AMOUNT = (
    Decimal("20.00") if CAMPAY_ENVIRONMENT == "DEV" else Decimal("1000.00")
)