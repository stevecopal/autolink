"""
Statuts centralisés des commandes Autolink.

Ce module est la source unique de vérité pour :
  - la liste des statuts possibles ;
  - l'ordre du workflow de livraison ;
  - les transitions autorisées ;
  - les rôles autorisés à déclencher chaque transition ;
  - les libellés et couleurs associés à chaque statut.

Aucun changement de statut ne doit être effectué en dehors de la couche de
service (``orders.services``) qui s'appuie exclusivement sur ces règles.
"""

from typing import Dict, List, Optional, Tuple, Union


class Status:
    """Constantes des statuts de commande."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    PROCESSING = "PROCESSING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    RECEIVED = "RECEIVED"
    COMPLETED = "COMPLETED"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


# Workflow canonique de livraison (linéaire)
WORKFLOW_ORDER: List[str] = [
    Status.PENDING,
    Status.CONFIRMED,
    Status.READY,
    Status.DELIVERED,
    Status.RECEIVED,
    Status.COMPLETED,
]

# Statuts auxiliaires conservés pour les autres flux (paiements / remboursements)
AUX_STATUSES: List[str] = [Status.PAID, Status.PROCESSING, Status.PICKED_UP, Status.REFUNDED]

# Rôles métier pouvant agir sur une commande
ROLE_BUYER = "buyer"      # l'acheteur (order.user)
ROLE_GARAGE = "garage"    # le propriétaire du garage
ROLE_ADMIN = "admin"      # administrateur / super-admin
ROLE_SYSTEM = "system"    # processus métier automatisé (backend)

STATUS_LABELS: Dict[str, str] = {
    Status.PENDING: "En attente",
    Status.CONFIRMED: "Confirmée",
    Status.PAID: "Payée",
    Status.PROCESSING: "En préparation",
    Status.READY: "Prête",
    Status.DELIVERED: "Livrée",
    Status.RECEIVED: "Reçue",
    Status.COMPLETED: "Terminée",
    Status.PICKED_UP: "Retirée",
    Status.CANCELLED: "Annulée",
    Status.REFUNDED: "Remboursée",
}

STATUS_COLORS: Dict[str, str] = {
    Status.PENDING: "gray",
    Status.CONFIRMED: "blue",
    Status.PAID: "green",
    Status.PROCESSING: "orange",
    Status.READY: "gold",
    Status.DELIVERED: "green",
    Status.RECEIVED: "blue",
    Status.COMPLETED: "green",
    Status.PICKED_UP: "green",
    Status.CANCELLED: "red",
    Status.REFUNDED: "purple",
}

# Champs d'horodatage associés aux statuts (renseignés automatiquement)
STATUS_TIMESTAMP_FIELD: Dict[str, str] = {
    Status.CONFIRMED: "confirmed_at",
    Status.READY: "ready_at",
    Status.DELIVERED: "delivered_at",
    Status.RECEIVED: "received_at",
    Status.COMPLETED: "completed_at",
    Status.CANCELLED: "cancelled_at",
}


class Transition:
    """Définition d'une transition métier contrôlée."""

    __slots__ = ("action", "label", "from_status", "to_status", "roles", "requires_note")

    def __init__(
        self,
        action: str,
        label: str,
        from_status: Union[str, Tuple[str, ...]],
        to_status: str,
        roles: Tuple[str, ...],
        requires_note: bool = False,
    ):
        self.action = action
        self.label = label
        self.from_status = from_status
        self.to_status = to_status
        self.roles = roles
        self.requires_note = requires_note

    @property
    def allowed_from(self) -> frozenset:
        if isinstance(self.from_status, (tuple, list, set, frozenset)):
            return frozenset(self.from_status)
        return frozenset([self.from_status])

    def matches(self, current_status: str) -> bool:
        return current_status in self.allowed_from


# ---------------------------------------------------------------------------
# Transitions autorisées (action -> Transition)
# ---------------------------------------------------------------------------
TRANSITIONS: Dict[str, Transition] = {
    # Le propriétaire du garage confirme la commande
    "CONFIRM": Transition(
        "CONFIRM",
        "Confirmer la commande",
        Status.PENDING,
        Status.CONFIRMED,
        (ROLE_GARAGE, ROLE_ADMIN),
    ),
    # Le propriétaire indique que la commande est prête
    "MARK_READY": Transition(
        "MARK_READY",
        "Marquer comme prête",
        Status.CONFIRMED,
        Status.READY,
        (ROLE_GARAGE, ROLE_ADMIN),
    ),
    # Le propriétaire du garage indique que la commande a été livrée
    "MARK_DELIVERED": Transition(
        "MARK_DELIVERED",
        "Marquer comme livrée",
        Status.READY,
        Status.DELIVERED,
        (ROLE_GARAGE, ROLE_ADMIN),
    ),
    # L'utilisateur confirme qu'il a récupéré / reçu la pièce
    "CONFIRM_RECEIPT": Transition(
        "CONFIRM_RECEIPT",
        "Confirmer la réception",
        Status.DELIVERED,
        Status.RECEIVED,
        (ROLE_BUYER, ROLE_ADMIN),
    ),
    # Clôture automatique uniquement lorsque les conditions métier sont satisfaites
    "COMPLETE": Transition(
        "COMPLETE",
        "Terminer la commande",
        Status.RECEIVED,
        Status.COMPLETED,
        (ROLE_SYSTEM, ROLE_ADMIN),
    ),
    # Annulation (acheteur, garage ou administrateur)
    "CANCEL": Transition(
        "CANCEL",
        "Annuler la commande",
        (Status.PENDING, Status.CONFIRMED),
        Status.CANCELLED,
        (ROLE_BUYER, ROLE_GARAGE, ROLE_ADMIN),
        requires_note=True,
    ),
}


def get_transition(action: str) -> Optional[Transition]:
    return TRANSITIONS.get(action)


def available_actions(current_status: str, roles: Tuple[str, ...]) -> List[str]:
    """Retourne les actions possibles pour un statut et un ensemble de rôles."""
    if not roles:
        return []
    result = []
    for action, spec in TRANSITIONS.items():
        if action == "COMPLETE":
            # La complétion est toujours pilotée par la logique métier backend.
            continue
        if not spec.matches(current_status):
            continue
        if set(roles) & set(spec.roles):
            result.append(action)
    return result