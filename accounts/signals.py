# accounts/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User as DjangoUser
from django.utils.translation import gettext_lazy as _

from .models import User
from garages.models import Garage


# --- Signal 1 : Attribuer SUPERUSER aux superusers créés via terminal ---
@receiver(post_save, sender=DjangoUser)
def assign_superuser_role(sender, instance, created, **kwargs):
    """
    Si un utilisateur est créé via `createsuperuser` (is_superuser=True),
    lui attribuer le rôle SUPERUSER.
    """
    try:
        if created and instance.is_superuser:
            user = User.objects.get(pk=instance.pk)
            user.role = User.Role.SUPERUSER
            user.save(update_fields=["role"])
    except Exception as e:
        print(f"[ERROR] Impossible d'attribuer le rôle SUPERUSER : {e}")


# --- Signal 2 : Stocker l'ancien approval_status avant sauvegarde ---
@receiver(pre_save, sender=Garage)
def store_old_approval_status(sender, instance, **kwargs):
    """
    Stocker l'ancien approval_status avant la sauvegarde pour détecter les changements.
    """
    if instance.pk:  # Si le garage existe déjà (pas une création)
        try:
            old_garage = Garage.objects.get(pk=instance.pk)
            instance._old_approval_status = old_garage.approval_status
        except Garage.DoesNotExist:
            pass


# --- Signal 3 : Transition USER → CLIENT quand approval_status passe à APPROVED ---
@receiver(post_save, sender=Garage)
def update_user_role_on_garage_approval(sender, instance, created, **kwargs):
    """
    Si un garage passe de PENDING à APPROVED, mettre à jour le rôle de l'utilisateur
    propriétaire à CLIENT (s'il est encore USER).
    """
    try:
        if not created:  # Seulement si le garage est mis à jour (pas à la création)
            # Vérifier si approval_status a changé de PENDING à APPROVED
            old_status = getattr(instance, "_old_approval_status", None)
            if (
                old_status == Garage.ApprovalStatus.PENDING
                and instance.approval_status == Garage.ApprovalStatus.APPROVED
            ):
                user = instance.owner
                if user.role == User.Role.USER:
                    user.role = User.Role.CLIENT
                    user.save(update_fields=["role"])
    except Exception as e:
        print(f"[ERROR] Impossible de mettre à jour le rôle USER → CLIENT : {e}")
