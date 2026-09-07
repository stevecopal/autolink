from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            'brand', 'model', 'nickname', 'year', 'engine',
            'fuel_type', 'transmission', 'license_plate', 'vin',
            'mileage', 'is_primary',
        ]
        widgets = {
            'brand': forms.Select(attrs={'id': 'brand-select', 'class': 'form-input'}),
            'model': forms.Select(attrs={'id': 'model-select', 'class': 'form-input'}),
            'nickname': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Ex: Ma Corolla')}),
            'year': forms.NumberInput(attrs={'class': 'form-input', 'min': 1950, 'max': 2030}),
            'engine': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Ex: 1.8')}),
            'fuel_type': forms.Select(attrs={'class': 'form-input'}),
            'transmission': forms.Select(attrs={'class': 'form-input'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Ex: ABC 123')}),
            'vin': forms.TextInput(attrs={'class': 'form-input', 'maxlength': 17, 'placeholder': _('17-character VIN')}),
            'mileage': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-auto-orange'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].help_text = ''
