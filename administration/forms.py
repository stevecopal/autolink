from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import City, Neighborhood
from .models import Announcement


class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de la ville'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-auto-200 text-auto-orange focus:ring-auto-orange'}),
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
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-auto-200 text-auto-orange focus:ring-auto-orange'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'link', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Titre de l\'annonce'}),
            'message': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Contenu de l\'annonce...'}),
            'link': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError(_('Le titre est obligatoire.'))
        return title

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError(_('Le message est obligatoire.'))
        return message
