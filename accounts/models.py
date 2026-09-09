import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Role(models.TextChoices):
        USER = 'USER', _('Utilisateur')
        CLIENT = 'CLIENT', _('Client')
        ADMIN = 'ADMIN', _('Administrateur')
        SUPERUSER = 'SUPERUSER', _('Super Utilisateur')

    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Actif')
        SUSPENDED = 'SUSPENDED', _('Suspendu')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        verbose_name=_('Statut du compte'),
    )
    phone = models.CharField(_('Téléphone'), max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    city = models.CharField(_('Ville'), max_length=100, blank=True)
    neighborhood = models.CharField(_('Quartier'), max_length=100, blank=True)
    address = models.TextField(_('Adresse'), blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    whatsapp = models.CharField(_('WhatsApp'), max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    @property
    def display_name(self):
        full = self.get_full_name()
        return full if full else self.username

    @property
    def is_account_active(self):
        return self.account_status == self.AccountStatus.ACTIVE

    @property
    def is_superadmin(self):
        return self.is_superuser or self.role == self.Role.SUPERUSER

    @property
    def is_admin_or_above(self):
        return self.role in (self.Role.ADMIN, self.Role.SUPERUSER) or self.is_superuser

    @property
    def is_client_or_above(self):
        return self.role in (self.Role.CLIENT, self.Role.ADMIN, self.Role.SUPERUSER) or self.is_superuser


class UserActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class ActionType(models.TextChoices):
        LOGIN = 'LOGIN', _('Connexion')
        LOGOUT = 'LOGOUT', _('Déconnexion')
        REGISTER = 'REGISTER', _('Inscription')
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', _('Changement mot de passe')
        PROFILE_UPDATE = 'PROFILE_UPDATE', _('Mise à jour profil')
        PAYMENT = 'PAYMENT', _('Paiement')
        REVIEW = 'REVIEW', _('Avis')
        SEARCH = 'SEARCH', _('Recherche')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=30, choices=ActionType.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Activité utilisateur')
        verbose_name_plural = _('Activités utilisateurs')


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Type(models.TextChoices):
        PAYMENT_SUCCESS = 'PAYMENT_SUCCESS', _('Paiement réussi')
        PAYMENT_FAILED = 'PAYMENT_FAILED', _('Paiement échoué')
        GARAGE_APPROVED = 'GARAGE_APPROVED', _('Garage approuvé')
        GARAGE_REJECTED = 'GARAGE_REJECTED', _('Garage rejeté')
        GARAGE_ACTIVATED = 'GARAGE_ACTIVATED', _('Garage activé')
        TICKET_REPLY = 'TICKET_REPLY', _('Réponse au ticket')
        ADMIN_MESSAGE = 'ADMIN_MESSAGE', _('Message de l\'administrateur')
        SYSTEM = 'SYSTEM', _('Système')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notif_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        verbose_name=_('Type'),
    )
    title = models.CharField(_('Titre'), max_length=200)
    message = models.TextField(_('Message'))
    link = models.CharField(_('Lien'), max_length=500, blank=True)
    is_read = models.BooleanField(_('Lu'), default=False)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f"{self.get_notif_type_display()} - {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read', 'updated_at'])

    @classmethod
    def unread_count(cls, user):
        return cls.objects.filter(user=user, is_read=False).count()

    @classmethod
    def create_payment_success(cls, user, garage, payment):
        return cls.objects.create(
            user=user,
            notif_type=cls.Type.PAYMENT_SUCCESS,
            title=_('Paiement confirmé'),
            message=_('Le paiement de %(amount)s %(currency)s pour le garage « %(garage)s » a été confirmé. Votre garage est maintenant actif.') % {
                'amount': payment.amount,
                'currency': payment.currency,
                'garage': garage.name,
            },
            link='/garages/%s/' % garage.slug,
            metadata={
                'payment_id': str(payment.pk),
                'garage_id': str(garage.pk),
                'amount': str(payment.amount),
                'currency': payment.currency,
            },
        )

    @classmethod
    def create_garage_approved(cls, user, garage):
        return cls.objects.create(
            user=user,
            notif_type=cls.Type.GARAGE_APPROVED,
            title=_('Garage approuvé'),
            message=_('Votre garage « %(garage)s » a été approuvé. Procédez au paiement pour l\'activer.') % {
                'garage': garage.name,
            },
            link='/garages/%s/' % garage.slug,
            metadata={'garage_id': str(garage.pk)},
        )

    @classmethod
    def create_admin_message(cls, user, title, message, link=''):
        return cls.objects.create(
            user=user,
            notif_type=cls.Type.ADMIN_MESSAGE,
            title=title,
            message=message,
            link=link,
        )
