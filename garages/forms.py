from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Garage, GarageVerification
from core.models import City, Neighborhood


class GarageForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True),
        label=_('Ville'),
        empty_label=_('Sélectionnez une ville'),
        required=True,
    )
    neighborhood = forms.ModelChoiceField(
        queryset=Neighborhood.objects.none(),
        label=_('Quartier'),
        empty_label=_('Sélectionnez un quartier'),
        required=True,
    )
    latitude = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput(), required=False
    )
    longitude = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput(), required=False
    )
    gps_accuracy = forms.DecimalField(
        max_digits=8, decimal_places=2, widget=forms.HiddenInput(), required=False
    )

    class Meta:
        model = Garage
        fields = [
            'name', 'description', 'phone', 'whatsapp', 'email',
            'address', 'city', 'neighborhood', 'photo',
            'latitude', 'longitude', 'gps_accuracy',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Nom du garage'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': _('Décrivez votre garage...'),
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
                'placeholder': _('Adresse complète'),
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'city' in self.data:
            try:
                city_id = int(self.data.get('city'))
                self.fields['neighborhood'].queryset = Neighborhood.objects.filter(
                    city_id=city_id, is_active=True
                )
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk and self.instance.city:
            self.fields['neighborhood'].queryset = Neighborhood.objects.filter(
                city=self.instance.city, is_active=True
            )

    def clean_neighborhood(self):
        neighborhood = self.cleaned_data.get('neighborhood')
        city = self.cleaned_data.get('city')
        if neighborhood and city and neighborhood.city != city:
            raise forms.ValidationError(_('Ce quartier n\'appartient pas à la ville sélectionnée.'))
        return neighborhood

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('La taille maximale est de 5 Mo.'))
            ext = photo.name.split('.')[-1].lower()
            if ext not in ('jpg', 'jpeg', 'png', 'webp'):
                raise forms.ValidationError(_('Formats acceptés : JPG, PNG, WebP.'))
        return photo


class GarageDocumentForm(forms.Form):
    document = forms.FileField(
        label=_('Justificatif du garage'),
        help_text=_('PDF ou Word, max 5 Mo'),
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input',
            'accept': '.pdf,.doc,.docx',
        }),
    )
    document_type = forms.ChoiceField(
        choices=GarageVerification.DocumentType.choices,
        label=_('Type de document'),
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            if document.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('La taille maximale est de 5 Mo.'))
            ext = document.name.split('.')[-1].lower()
            if ext not in ('pdf', 'doc', 'docx'):
                raise forms.ValidationError(_('Seuls les fichiers PDF et Word sont acceptés.'))
        return document
