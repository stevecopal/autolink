# accounts/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User as DjangoUser
from django.utils.translation import gettext_lazy as _

from .models import User
from garages.models import Garage


@receiver(post_save, sender=DjangoUser)
def assign_superuser_role(sender, instance, created, **kwargs):
    try:
        if created and instance.is_superuser:
            user = User.objects.get(pk=instance.pk)
            user.role = User.Role.SUPERUSER
            user.save(update_fields=["role"])
    except Exception as e:
        print(f"[ERROR] Impossible d'attribuer le role SUPERUSER : {e}")


@receiver(pre_save, sender=Garage)
def store_old_approval_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_garage = Garage.objects.get(pk=instance.pk)
            instance._old_approval_status = old_garage.approval_status
        except Garage.DoesNotExist:
            pass


@receiver(post_save, sender=Garage)
def update_user_role_on_garage_approval(sender, instance, created, **kwargs):
    """
    When a garage goes from PENDING to APPROVED, create a notification for the owner.
    The actual USER->CLIENT role upgrade happens upon successful payment confirmation.
    """
    try:
        if not created:
            old_status = getattr(instance, "_old_approval_status", None)
            if (
                old_status == Garage.ApprovalStatus.PENDING
                and instance.approval_status == Garage.ApprovalStatus.APPROVED
            ):
                from .models import Notification
                Notification.create_garage_approved(instance.owner, instance)
    except Exception as e:
        print(f"[ERROR] Impossible de traiter l'approbation du garage : {e}")
