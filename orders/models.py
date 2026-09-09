import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Panier')
        verbose_name_plural = _('Paniers')

    def __str__(self):
        return f"Panier de {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.select_related('part').all())

    @property
    def item_count(self):
        return self.items.count()


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey('catalog.Part', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'part']
        verbose_name = _('Article du panier')
        verbose_name_plural = _('Articles du panier')

    def __str__(self):
        return f"{self.part.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.part.price * self.quantity


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        CONFIRMED = 'CONFIRMED', _('Confirmée')
        PAID = 'PAID', _('Payée')
        PROCESSING = 'PROCESSING', _('En préparation')
        READY = 'READY', _('Prête')
        PICKED_UP = 'PICKED_UP', _('Retirée')
        DELIVERED = 'DELIVERED', _('Livrée')
        CANCELLED = 'CANCELLED', _('Annulée')
        REFUNDED = 'REFUNDED', _('Remboursée')

    class FulfillmentType(models.TextChoices):
        PICKUP = 'PICKUP', _('Click & Collect')
        DELIVERY = 'DELIVERY', _('Livraison')

    order_number = models.CharField(_('Numéro de commande'), max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    garage = models.ForeignKey('garages.Garage', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    fulfillment_type = models.CharField(max_length=20, choices=FulfillmentType.choices, default=FulfillmentType.PICKUP)

    subtotal = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    service_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    pickup_code = models.CharField(_('Code de retrait'), max_length=6, blank=True, editable=False)
    pickup_confirmed = models.BooleanField(default=False)

    delivery_address = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)

    notes = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Commande')
        verbose_name_plural = _('Commandes')

    def __str__(self):
        return f"Commande {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"AL-{uuid.uuid4().hex[:8].upper()}"
        if not self.pickup_code:
            self.pickup_code = f"{uuid.uuid4().int % 10000:04d}"
        super().save(*args, **kwargs)

    def get_timeline(self):
        steps = [
            ('PENDING', 'Commande passée', True),
            ('PAID', 'Paiement confirmé', self.status in ['PAID', 'PROCESSING', 'READY', 'PICKED_UP', 'DELIVERED']),
            ('CONFIRMED', 'Vendeur confirmé', self.status in ['CONFIRMED', 'PROCESSING', 'READY', 'PICKED_UP', 'DELIVERED']),
            ('PROCESSING', 'En préparation', self.status in ['PROCESSING', 'READY', 'PICKED_UP', 'DELIVERED']),
            ('READY', 'Commande prête', self.status in ['READY', 'PICKED_UP', 'DELIVERED']),
            ('PICKED_UP', 'Retirée', self.status in ['PICKED_UP', 'DELIVERED']),
        ]
        return steps

    @property
    def status_label(self):
        labels = {
            'PENDING': 'En attente',
            'CONFIRMED': 'Confirmée',
            'PAID': 'Payée',
            'PROCESSING': 'En préparation',
            'READY': 'Prête',
            'PICKED_UP': 'Retirée',
            'DELIVERED': 'Livrée',
            'CANCELLED': 'Annulée',
            'REFUNDED': 'Remboursée',
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self):
        colors = {
            'PENDING': 'gray',
            'CONFIRMED': 'blue',
            'PAID': 'green',
            'PROCESSING': 'orange',
            'READY': 'green',
            'PICKED_UP': 'green',
            'DELIVERED': 'green',
            'CANCELLED': 'red',
            'REFUNDED': 'purple',
        }
        return colors.get(self.status, 'gray')


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    part = models.ForeignKey('catalog.Part', on_delete=models.SET_NULL, null=True)
    part_name = models.CharField(max_length=300)
    part_price = models.DecimalField(max_digits=10, decimal_places=0)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    install_service = models.BooleanField(default=False)
    install_price = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    class Meta:
        verbose_name = _('Article de commande')
        verbose_name_plural = _('Articles de commande')

    def __str__(self):
        return f"{self.part_name} x{self.quantity}"

    def save(self, *args, **kwargs):
        self.subtotal = self.part_price * self.quantity
        super().save(*args, **kwargs)
