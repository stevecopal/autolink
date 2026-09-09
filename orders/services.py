"""
Couche de service des commandes.

Toute modification du statut d'une commande DOIT passer par
``apply_transition`` qui vérifie, côté backend :
  - que l'acteur possède le rôle requis pour l'action ;
  - que le statut courant autorise la transition ;
  - que les conditions métier (ex. clôture) sont satisfaites.

Cela garantit qu'aucun utilisateur ne peut modifier arbitrairement un statut.
"""

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from . import status as st
from .models import Order


def _is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_admin_or_above)


def _is_garage_owner(order: Order, user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and order.garage is not None
        and order.garage.owner_id == user.pk
    )


def roles_for(order: Order, user) -> tuple:
    """Rôles que l'utilisateur détient pour cette commande."""
    if not user or not user.is_authenticated:
        return ()
    roles = []
    if order.user_id == user.pk:
        roles.append(st.ROLE_BUYER)
    if _is_garage_owner(order, user):
        roles.append(st.ROLE_GARAGE)
    if _is_admin(user):
        roles.append(st.ROLE_ADMIN)
    return tuple(roles)


def can_perform(order: Order, action: str, user) -> bool:
    """Une transition est-elle autorisée pour cet utilisateur sur cette commande ?"""
    if not user or not user.is_authenticated:
        return False
    spec = st.get_transition(action)
    if spec is None:
        return False
    if not spec.matches(order.status):
        return False
    user_roles = roles_for(order, user)
    return bool(set(user_roles) & set(spec.roles))


def available_actions(order: Order, user) -> list:
    """Liste des actions que l'utilisateur peut déclencher sur cette commande."""
    return st.available_actions(order.status, roles_for(order, user))


def business_conditions_met(order: Order) -> bool:
    """
    Conditions métier satisfaites pour clôturer (COMPLETED) une commande.

    Une commande ne devient COMPLETED que lorsque :
      - l'utilisateur a confirmé avoir reçu la pièce (statut RECEIVED) ;
      - la commande n'est ni annulée ni remboursée ;
      - aucun remboursement n'est en cours.
    """
    if order.status != Order.Status.RECEIVED:
        return False
    if order.status in (Order.Status.CANCELLED, Order.Status.REFUNDED):
        return False
    try:
        Refund = __import__("payments.models", fromlist=["Refund"]).Refund
        blocked = order.refunds.filter(
            status__in=[Refund.Status.PENDING, Refund.Status.PROCESSING]
        ).exists()
        if blocked:
            return False
    except (ImportError, AttributeError):
        # Le module paiements n'est pas indispensable pour la clôture.
        pass
    return True


def _dispatch_notifications(order: Order, action: str, actor):
    from notifications.services import notify_order_event

    event_by_action = {
        "CONFIRM": "confirmed",
        "MARK_DELIVERED": "delivered",
        "CONFIRM_RECEIPT": "picked_up",
        "COMPLETE": "completed",
        "CANCEL": "cancelled",
    }
    event = event_by_action.get(action)
    if event:
        notify_order_event(order, event, actor=actor)


def _do_transition(order: Order, action: str, actor, note: str = ""):
    spec = st.get_transition(action)
    order.status = spec.to_status
    order.save(actor=actor, note=note)
    _dispatch_notifications(order, action, actor)


def apply_transition(order: Order, action: str, actor, note: str = "") -> Order:
    """
    Applique une transition contrôlée côté backend.

    Lève PermissionDenied si l'acteur ne peut pas déclencher l'action,
    ou si la transition n'est pas valide depuis le statut courant.
    """
    import django.db.transaction as transaction

    spec = st.get_transition(action)
    if spec is None:
        raise ValueError(_("Action inconnue."))
    if not can_perform(order, action, actor):
        raise PermissionDenied(
            _("Vous n'êtes pas autorisé à effectuer cette action sur cette commande.")
        )
    if spec.requires_note and not note:
        raise PermissionDenied(_("Une raison est requise."))

    with transaction.atomic():
        _do_transition(order, action, actor, note=note)

        # Clôture automatique (COMPLETED) lorsque les conditions métier le permettent.
        if action == "CONFIRM_RECEIPT" and business_conditions_met(order):
            order.status = st.Status.COMPLETED
            order.save(
                actor=actor,
                note=_(
                    "Conditions métier satisfaites : pièce récupérée par le client."
                ),
            )
            if order.garage and order.garage.owner_id != actor.pk:
                from notifications.models import Notification

                Notification.objects.create(
                    user=order.garage.owner,
                    category=Notification.Category.ORDER,
                    title=_("Commande terminée"),
                    message=_("La commande %(num)s est terminée.")
                    % {"num": order.order_number},
                    link=f"/commandes/{order.order_number}/",
                )

    return order


def cancel_order(order: Order, actor, note: str = "") -> Order:
    """Annule une commande via la transition contrôlée CANCEL."""
    return apply_transition(order, "CANCEL", actor, note=note)
