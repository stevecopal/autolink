from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import City, Neighborhood
from .models import Announcement


class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name', 'slug', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom de la ville'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-de-la-ville'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-auto-200 text-auto-orange focus:ring-auto-orange'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        if not slug:
            slug = slugify(self.cleaned_data.get('name', ''))
        if not slug:
            raise forms.ValidationError(_('Le slug est obligatoire.'))
        qs = City.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Ce slug existe déjà.'))
        return slug


class NeighborhoodForm(forms.ModelForm):
    class Meta:
        model = Neighborhood
        fields = ['city', 'name', 'slug', 'is_active']
        widgets = {
            'city': forms.Select(attrs={'class': 'form-input'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom du quartier'}),
            'slug': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'slug-du-quartier'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-auto-200 text-auto-orange focus:ring-auto-orange'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError(_('Le nom est obligatoire.'))
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        city = self.cleaned_data.get('city')
        if not slug:
            slug = slugify(self.cleaned_data.get('name', ''))
        if not slug:
            raise forms.ValidationError(_('Le slug est obligatoire.'))
        if city:
            qs = Neighborhood.objects.filter(city=city, slug=slug)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('Ce slug existe déjà pour cette ville.'))
        return slug


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
