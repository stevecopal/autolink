import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(_('Catégorie'), max_length=200)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    icon = models.CharField(_('Icône'), max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _('Catégorie')
        verbose_name_plural = _('Catégories')

    def __str__(self):
        return self.name


class Part(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Condition(models.TextChoices):
        NEW = 'NEW', _('Neuf')
        USED = 'USED', _('Occasion')
        REFURBISHED = 'REFURBISHED', _('Reconditionné')

    class StockStatus(models.TextChoices):
        IN_STOCK = 'IN_STOCK', _('Disponible')
        LOW_STOCK = 'LOW_STOCK', _('Stock faible')
        OUT_OF_STOCK = 'OUT_OF_STOCK', _('Indisponible')

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parts')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='parts')
    name = models.CharField(_('Nom de la pièce'), max_length=300)
    slug = models.SlugField(unique=True)
    description = models.TextField(_('Description'), blank=True)

    reference_oem = models.CharField(_('Référence OEM'), max_length=100, blank=True)
    reference_fabricant = models.CharField(_('Référence fabricant'), max_length=100, blank=True)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.NEW)

    price = models.DecimalField(_('Prix'), max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField(_('Stock'), default=0)
    stock_status = models.CharField(max_length=20, choices=StockStatus.choices, default=StockStatus.OUT_OF_STOCK)

    photo = models.ImageField(upload_to='parts/', blank=True, null=True)
    garage = models.ForeignKey('garages.Garage', on_delete=models.SET_NULL, null=True, blank=True, related_name='parts')

    warranty_months = models.PositiveIntegerField(_('Garantie (mois)'), default=0)
    is_active = models.BooleanField(default=True)
    total_views = models.PositiveIntegerField(default=0)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city = models.CharField(_('Ville'), max_length=100, blank=True)
    neighborhood = models.CharField(_('Quartier'), max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Pièce')
        verbose_name_plural = _('Pièces')

    def __str__(self):
        return self.name

    def update_stock_status(self):
        if self.stock == 0:
            self.stock_status = self.StockStatus.OUT_OF_STOCK
        elif self.stock <= 3:
            self.stock_status = self.StockStatus.LOW_STOCK
        else:
            self.stock_status = self.StockStatus.IN_STOCK
        self.save(update_fields=['stock_status'])

    @property
    def is_available(self):
        return self.stock_status in [self.StockStatus.IN_STOCK, self.StockStatus.LOW_STOCK]

    @property
    def stock_label(self):
        if self.stock_status == self.StockStatus.IN_STOCK:
            return _('Disponible')
        elif self.stock_status == self.StockStatus.LOW_STOCK:
            return _('Stock faible')
        return _('Indisponible')

    @property
    def stock_color(self):
        if self.stock_status == self.StockStatus.IN_STOCK:
            return 'green'
        elif self.stock_status == self.StockStatus.LOW_STOCK:
            return 'orange'
        return 'red'


class PartPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='parts/photos/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Photo de {self.part.name}"
