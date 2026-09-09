# accounts/services.py
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def admin_users():
    """Retourne tous les utilisateurs ADMIN/SUPERUSER actifs, y compris les superusers Django."""
    return User.objects.filter(
        is_active=True,
    ).filter(Q(is_superuser=True) | Q(role__in=[User.Role.ADMIN, User.Role.SUPERUSER]))
