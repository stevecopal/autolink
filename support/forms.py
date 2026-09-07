from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Ticket, TicketMessage, AssistanceRequest


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['category', 'order', 'garage', 'subject', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input'}),
            'order': forms.Select(attrs={'class': 'form-input'}),
            'garage': forms.Select(attrs={'class': 'form-input'}),
            'subject': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Brief summary')}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 4}),
        }


class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': _('Your message...')}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }


class AssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = AssistanceRequest
        fields = ['issue_type', 'description', 'address']
        widgets = {
            'issue_type': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
