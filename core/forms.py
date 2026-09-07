from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Votre nom complet'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': _('votre@email.com'),
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('+237 6XX XXX XXX'),
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Sujet de votre message'),
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 5,
                'placeholder': _('Décrivez votre demande...'),
            }),
        }
