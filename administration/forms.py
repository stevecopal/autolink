from django import forms
from django.utils.translation import gettext_lazy as _

from core.models import City, Neighborhood


class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de la ville'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-blue-200 text-blue-500 focus:ring-blue-500'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name


class NeighborhoodForm(forms.ModelForm):
    class Meta:
        model = Neighborhood
        fields = ['city', 'name', 'is_active']
        widgets = {
            'city': forms.Select(attrs={'class': 'form-input'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom du quartier'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-blue-200 text-blue-500 focus:ring-blue-500'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name
