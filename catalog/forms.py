from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Part, PartRequest


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = [
            'name', 'category', 'brand', 'reference_oem', 'reference_fabricant',
            'condition', 'description', 'price', 'stock', 'photo',
            'garage', 'warranty_months', 'city', 'neighborhood',
            'latitude', 'longitude',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Part name')}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'brand': forms.Select(attrs={'class': 'form-input'}),
            'reference_oem': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('OEM reference')}),
            'reference_fabricant': forms.TextInput(attrs={'class': 'form-input'}),
            'condition': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'stock': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input'}),
            'garage': forms.Select(attrs={'class': 'form-input'}),
            'warranty_months': forms.NumberInput(attrs={'class': 'form-input', 'min': 0}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-input'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }


class PartRequestForm(forms.ModelForm):
    class Meta:
        model = PartRequest
        fields = [
            'vehicle', 'part_name', 'reference', 'description',
            'photo', 'quantity', 'city', 'neighborhood', 'urgency',
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-input'}),
            'part_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Part name')}),
            'reference': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-input'}),
            'urgency': forms.Select(attrs={'class': 'form-input'}),
        }
