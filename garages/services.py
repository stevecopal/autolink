"""
Services métier pour la gestion des garages et des rôles.

Gère la logique de promotion USER → CLIENT lors de l'approbation d'un garage.
"""

import logging

from django.utils import timezone

logger = logging.getLogger("autolink")


def approve_garage(garage, admin_user=None):
    """
    Approuve un garage et promeut le propriétaire en CLIENT si nécessaire.
    Les ADMIN et SUPERUSER ne sont pas promus (ils ont déjà un rôle supérieur).

    Args:
        garage: Instance du modèle Garage
        admin_user: L'administrateur qui approuve (optionnel)

    Returns:
        dict avec 'promoted' (bool) et 'message' (str)
    """
    from accounts.models import User

    garage.verification_status = garage.VerificationStatus.APPROVED
    garage.approval_status = garage.ApprovalStatus.APPROVED
    garage.payment_status = garage.PaymentStatus.UNPAID
    garage.activation_status = garage.ActivationStatus.INACTIVE
    garage.rejection_reason = ""
    garage.save(
        update_fields=[
            "verification_status",
            "approval_status",
            "payment_status",
            "activation_status",
            "rejection_reason",
            "updated_at",
        ]
    )
    from notifications.services import notify_garage_event

    notify_garage_event(garage, "approved")

    owner = garage.owner
    promoted = False

    if (
        owner.role not in (User.Role.CLIENT, User.Role.ADMIN, User.Role.SUPERUSER)
        and not owner.is_superuser
    ):
        owner.role = User.Role.CLIENT
        owner.save(update_fields=["role"])
        promoted = True
        logger.info(
            "Utilisateur %s promu en CLIENT (garage %s approuvé par %s)",
            owner.username,
            garage.name,
            admin_user.username if admin_user else "systeme",
        )

    return {
        "promoted": promoted,
        "message": (
            f"Garage '{garage.name}' approuvé. {owner.username} promu en CLIENT."
            if promoted
            else f"Garage '{garage.name}' approuvé."
        ),
    }


def reject_garage(garage, reason="", admin_user=None):
    """
    Rejette un garage. Le propriétaire reste USER s'il n'a aucun autre garage approuvé.
    Les ADMIN et SUPERUSER ne sont jamais rétrogradés.

    Args:
        garage: Instance du modèle Garage
        reason: Raison du rejet
        admin_user: L'administrateur qui rejette (optionnel)

    Returns:
        dict avec 'demoted' (bool) et 'message' (str)
    """
    from accounts.models import User

    garage.verification_status = garage.VerificationStatus.REJECTED
    garage.approval_status = garage.ApprovalStatus.REJECTED
    garage.activation_status = garage.ActivationStatus.INACTIVE
    garage.rejection_reason = reason
    garage.save(
        update_fields=[
            "verification_status",
            "approval_status",
            "activation_status",
            "rejection_reason",
            "updated_at",
        ]
    )
    from notifications.services import notify_garage_event

    notify_garage_event(garage, "rejected", reason=reason)

    owner = garage.owner
    demoted = False

    if owner.role in (User.Role.ADMIN, User.Role.SUPERUSER) or owner.is_superuser:
        return {
            "demoted": False,
            "message": f"Garage '{garage.name}' rejeté.",
        }

    has_approved = (
        owner.garages.filter(approval_status=garage.ApprovalStatus.APPROVED)
        .exclude(pk=garage.pk)
        .exists()
    )

    if not has_approved and owner.role == User.Role.CLIENT:
        owner.role = User.Role.USER
        owner.save(update_fields=["role"])
        demoted = True
        logger.info(
            "Utilisateur %s rétrogradé en USER (garage %s rejeté par %s)",
            owner.username,
            garage.name,
            admin_user.username if admin_user else "systeme",
        )

    return {
        "demoted": demoted,
        "message": (
            f"Garage '{garage.name}' rejeté. {owner.username} rétrogradé en USER."
            if demoted
            else f"Garage '{garage.name}' rejeté."
        ),
    }


def suspend_garage(garage, admin_user=None):
    """
    Suspend un garage. Le propriétaire reste CLIENT s'il a d'autres garages approuvés.

    Args:
        garage: Instance du modèle Garage
        admin_user: L'administrateur qui suspend (optionnel)

    Returns:
        dict avec 'message' (str)
    """
    garage.verification_status = garage.VerificationStatus.SUSPENDED
    garage.activation_status = garage.ActivationStatus.SUSPENDED
    garage.save(
        update_fields=["verification_status", "activation_status", "updated_at"]
    )

    logger.info(
        "Garage %s suspendu par %s",
        garage.name,
        admin_user.username if admin_user else "systeme",
    )

    return {
        "message": f"Garage '{garage.name}' suspendu.",
    }


def update_garage_availability(garage, availability_status, message=""):
    """
    Met à jour la disponibilité d'un garage.

    Args:
        garage: Instance du modèle Garage
        availability_status: Nouveau statut de disponibilité
        message: Message optionnel de disponibilité

    Returns:
        dict avec 'message' (str)
    """
    from garages.models import Garage

    if garage.approval_status != Garage.ApprovalStatus.APPROVED:
        return {
            "success": False,
            "message": "Seuls les garages approuvés peuvent modifier leur disponibilité.",
        }

    garage.availability_status = availability_status
    garage.availability_message = message
    garage.save(
        update_fields=["availability_status", "availability_message", "updated_at"]
    )

    return {
        "success": True,
        "message": "Disponibilité mise à jour.",
    }
