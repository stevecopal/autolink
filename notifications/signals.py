from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from garages.models import Garage
from payments.models import Payment


@receiver(pre_save, sender=Payment)
def remember_payment_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_status = None
    else:
        instance._notification_previous_status = (
            sender.objects.filter(pk=instance.pk)
            .values_list("status", flat=True)
            .first()
        )


@receiver(post_save, sender=Payment)
def notify_payment_status(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_status", None)
    if instance.status == Payment.Status.SUCCESS and (
        created or previous != instance.status
    ):
        from .services import notify_payment_event

        notify_payment_event(instance, "confirmed")
    elif instance.status == Payment.Status.FAILED and previous != instance.status:
        from .services import notify_payment_event

        notify_payment_event(instance, "failed")


@receiver(pre_save, sender=Garage)
def remember_garage_activation(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_previous_activation = None
    else:
        instance._notification_previous_activation = (
            sender.objects.filter(pk=instance.pk)
            .values_list("activation_status", flat=True)
            .first()
        )


@receiver(post_save, sender=Garage)
def notify_garage_activation(sender, instance, created, **kwargs):
    previous = getattr(instance, "_notification_previous_activation", None)
    if (
        instance.activation_status == Garage.ActivationStatus.ACTIVE
        and previous != instance.activation_status
    ):
        from .services import notify_garage_event

        notify_garage_event(instance, "activated")
