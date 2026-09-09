from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from .models import Part


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = [
            'name', 'category', 'reference_oem', 'reference_fabricant',
            'condition', 'description', 'price', 'stock', 'photo',
            'warranty_months', 'city', 'neighborhood',
            'latitude', 'longitude',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Nom de la pièce'),
                'autofocus': True,
            }),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'reference_oem': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ex: OEM-12345'),
            }),
            'reference_fabricant': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ex: FAB-67890'),
            }),
            'condition': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': _('Description de la pièce...'),
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'step': '50',
                'placeholder': '0',
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'step': '1',
                'placeholder': '0',
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
            'warranty_months': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0',
                'step': '1',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ex: Douala'),
            }),
            'neighborhood': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ex: Akwa'),
            }),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['price'].required = True

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            raise forms.ValidationError(_('Le prix est obligatoire.'))
        if price < 0:
            raise forms.ValidationError(_('Le prix ne peut pas être négatif.'))
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is None:
            return 0
        if stock < 0:
            raise forms.ValidationError(_('Le stock ne peut pas être négatif.'))
        return stock

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name.strip()

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug or (self.instance and self.instance.pk is None):
            base_slug = slugify(instance.name)
            if not base_slug:
                base_slug = 'part'
            slug = base_slug
            counter = 1
            while Part.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance
