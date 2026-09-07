from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', _('Client')
        GARAGE = 'GARAGE', _('Garage')
        VENDEUR = 'VENDEUR', _('Vendeur')
        ADMIN = 'ADMIN', _('Administrateur')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
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


class UserActivity(models.Model):
    class ActionType(models.TextChoices):
        LOGIN = 'LOGIN', _('Connexion')
        LOGOUT = 'LOGOUT', _('Déconnexion')
        REGISTER = 'REGISTER', _('Inscription')
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', _('Changement mot de passe')
        PROFILE_UPDATE = 'PROFILE_UPDATE', _('Mise à jour profil')
        VEHICLE_ADD = 'VEHICLE_ADD', _('Ajout véhicule')
        ORDER_CREATE = 'ORDER_CREATE', _('Création commande')
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
