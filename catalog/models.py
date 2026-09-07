from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
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

    brand = models.ForeignKey('vehicles.Brand', on_delete=models.SET_NULL, null=True, blank=True, related_name='parts')
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
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='parts/photos/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Photo de {self.part.name}"


class Compatibility(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', _('Compatible')
        PROBABLE = 'PROBABLE', _('Probablement compatible')
        NOT_CONFIRMED = 'NOT_CONFIRMED', _('Compatibilité non confirmée')
        NOT_COMPATIBLE = 'NOT_COMPATIBLE', _('Non compatible')

    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name='compatibilities')
    brand = models.ForeignKey('vehicles.Brand', on_delete=models.CASCADE)
    model_vehicle = models.ForeignKey('vehicles.ModelVehicle', on_delete=models.CASCADE, null=True, blank=True)
    year_min = models.PositiveIntegerField(_('Année min'), null=True, blank=True)
    year_max = models.PositiveIntegerField(_('Année max'), null=True, blank=True)
    engine = models.CharField(_('Moteur'), max_length=50, blank=True)
    fuel_type = models.CharField(max_length=20, blank=True)
    transmission = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_CONFIRMED)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Compatibilité')
        verbose_name_plural = _('Compatibilités')

    def __str__(self):
        return f"{self.part.name} - {self.brand.name}"

    def is_compatible_with_vehicle(self, vehicle):
        if self.brand != vehicle.brand:
            return self.Status.NOT_COMPATIBLE
        if self.model_vehicle and self.model_vehicle != vehicle.model:
            return self.Status.NOT_COMPATIBLE
        if vehicle.year:
            if self.year_min and vehicle.year < self.year_min:
                return self.Status.NOT_COMPATIBLE
            if self.year_max and vehicle.year > self.year_max:
                return self.Status.NOT_COMPATIBLE
        if self.engine and vehicle.engine and self.engine != vehicle.engine:
            return self.Status.PROBABLE
        if self.fuel_type and vehicle.fuel_type and self.fuel_type != vehicle.fuel_type:
            return self.Status.NOT_COMPATIBLE
        return self.status


class PartRequest(models.Model):
    class Urgency(models.TextChoices):
        LOW = 'LOW', _('Pas urgent')
        MEDIUM = 'MEDIUM', _('Modéré')
        HIGH = 'HIGH', _('Urgent')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='part_requests')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.SET_NULL, null=True, blank=True)
    part_name = models.CharField(_('Pièce recherchée'), max_length=300)
    reference = models.CharField(_('Référence'), max_length=100, blank=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='part_requests/', blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    city = models.CharField(max_length=100, blank=True)
    neighborhood = models.CharField(max_length=100, blank=True)
    urgency = models.CharField(max_length=10, choices=Urgency.choices, default=Urgency.MEDIUM)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Demande de pièce')
        verbose_name_plural = _('Demandes de pièces')

    def __str__(self):
        return f"Demande: {self.part_name} par {self.user.username}"
