from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Garage


class GarageForm(forms.ModelForm):
    class Meta:
        model = Garage
        fields = [
            'name', 'description', 'phone', 'whatsapp', 'email',
            'address', 'city', 'neighborhood',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Garage name'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': _('Describe your garage...'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+237 6XX XXX XXX',
            }),
            'whatsapp': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+237 6XX XXX XXX',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'garage@example.com',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 2,
                'placeholder': _('Full address'),
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('City'),
            }),
            'neighborhood': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Neighborhood'),
            }),
        }
