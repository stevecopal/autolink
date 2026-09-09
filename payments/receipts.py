from django.db import transaction

from .models import Payment, Receipt


def create_or_update_receipt(payment):
    garage = payment.garage
    owner = garage.owner if garage else None
    with transaction.atomic():
        receipt, _ = Receipt.objects.get_or_create(
            payment=payment,
            defaults={
                "garage": garage,
                "owner": owner,
                "amount": payment.amount,
                "currency": payment.currency,
                "provider": payment.provider,
                "status": payment.status,
            },
        )
        changed = []
        for field, value in {
            "garage": garage,
            "owner": owner,
            "amount": payment.amount,
            "currency": payment.currency,
            "provider": payment.provider,
            "status": payment.status,
        }.items():
            if getattr(receipt, field) != value:
                setattr(receipt, field, value)
                changed.append(field)
        if changed:
            receipt.save(update_fields=changed + ["updated_at"])
    return receipt
