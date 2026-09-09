import os
import mimetypes

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Ticket, TicketMessage, AssistanceRequest

ALLOWED_MIME_TYPES = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx']
MAX_FILE_SIZE = 5 * 1024 * 1024


class TicketForm(forms.ModelForm):
    evidence = forms.FileField(
        label=_('Preuve (optionnel)'),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,application/pdf,.doc,.docx',
        }),
    )

    class Meta:
        model = Ticket
        fields = ['order', 'garage', 'subject', 'description', 'evidence']
        widgets = {
            'order': forms.Select(attrs={'class': 'form-input', 'id': 'ticket-order'}),
            'garage': forms.Select(attrs={'class': 'form-input', 'id': 'ticket-garage'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Ex: Pièce défectueuse après installation'),
                'maxlength': 300,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 6,
                'placeholder': _('Décrivez votre problème en détail...'),
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            from orders.models import Order
            self.fields['order'].queryset = Order.objects.filter(
                user=user, garage__isnull=False
            ).select_related('garage').order_by('-created_at')
            self.fields['order'].empty_label = _('— Sélectionnez une commande —')
            self.fields['garage'].queryset = self.fields['order'].queryset.values_list(
                'garage', flat=True
            ).distinct()
            from garages.models import Garage
            garage_ids = list(self.fields['garage'].queryset)
            self.fields['garage'].queryset = Garage.objects.filter(pk__in=garage_ids)
            self.fields['garage'].empty_label = _('— Sélectionnez un garage —')
        else:
            self.fields['order'].queryset = Order.objects.none()
            self.fields['garage'].queryset = Ticket._meta.get_field('garage').related_model.objects.none()

    def clean_order(self):
        order = self.cleaned_data.get('order')
        if order and self.user and order.user != self.user:
            raise forms.ValidationError(_('Cette commande ne vous appartient pas.'))
        return order

    def clean_garage(self):
        garage = self.cleaned_data.get('garage')
        order = self.cleaned_data.get('order')
        if order and garage and order.garage != garage:
            raise forms.ValidationError(
                _('Ce garage ne correspond pas à la commande sélectionnée.')
            )
        return garage

    def clean_evidence(self):
        evidence = self.cleaned_data.get('evidence')
        if evidence:
            if evidence.size > MAX_FILE_SIZE:
                raise ValidationError(
                    _('Le fichier ne doit pas dépasser %(size)s Mo.') % {'size': 5}
                )
            mime_type, _ = mimetypes.guess_type(evidence.name)
            if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                raise ValidationError(
                    _('Type de fichier non autorisé. Formats acceptés : images (JPG, PNG, GIF, WebP), PDF, Word.')
                )
            ext = os.path.splitext(evidence.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    _('Extension non autorisée. Formats acceptés : %(formats)s.') % {
                        'formats': ', '.join(ALLOWED_EXTENSIONS)
                    }
                )
        return evidence

    def clean(self):
        cleaned_data = super().clean()
        order = cleaned_data.get('order')
        garage = cleaned_data.get('garage')
        if order and not garage:
            cleaned_data['garage'] = order.garage
        return cleaned_data


class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 3,
                'placeholder': _('Écrivez votre réponse ici...'),
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*,application/pdf,.doc,.docx',
            }),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > MAX_FILE_SIZE:
                raise ValidationError(
                    _('Le fichier ne doit pas dépasser %(size)s Mo.') % {'size': 5}
                )
            mime_type, _ = mimetypes.guess_type(attachment.name)
            if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                raise ValidationError(
                    _('Type de fichier non autorisé. Formats acceptés : images, PDF, Word.')
                )
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    _('Extension non autorisée.')
                )
        return attachment


class AdminTicketReplyForm(forms.Form):
    message = forms.CharField(
        label=_('Réponse'),
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': _('Écrivez votre réponse ici...'),
        }),
    )
    attachment = forms.FileField(
        label=_('Pièce jointe (optionnel)'),
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*,application/pdf,.doc,.docx',
        }),
    )
    new_status = forms.ChoiceField(
        label=_('Changer le statut'),
        choices=Ticket.Status.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            if attachment.size > MAX_FILE_SIZE:
                raise ValidationError(
                    _('Le fichier ne doit pas dépasser %(size)s Mo.') % {'size': 5}
                )
            mime_type, _ = mimetypes.guess_type(attachment.name)
            if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                raise ValidationError(
                    _('Type de fichier non autorisé.')
                )
        return attachment


class AssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = AssistanceRequest
        fields = ['issue_type', 'description', 'address']
        widgets = {
            'issue_type': forms.Select(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }
