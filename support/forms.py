from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Ticket, TicketMessage, AssistanceRequest


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['category', 'order', 'part', 'garage', 'subject', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-input', 'id': 'ticket-category'}),
            'order': forms.Select(attrs={'class': 'form-input', 'id': 'ticket-order'}),
            'part': forms.Select(attrs={'class': 'form-input', 'id': 'ticket-part'}),
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
            self.fields['order'].queryset = Order.objects.filter(user=user).order_by('-created_at')
            self.fields['order'].empty_label = _('— Aucune commande —')
            self.fields['part'].empty_label = _('— Aucune pièce —')
            self.fields['garage'].empty_label = _('— Aucun garage —')
        else:
            self.fields['order'].queryset = Order.objects.none()
            self.fields['part'].queryset = Ticket._meta.get_field('part').related_model.objects.none()
            self.fields['garage'].queryset = Ticket._meta.get_field('garage').related_model.objects.none()

    def clean_order(self):
        order = self.cleaned_data.get('order')
        if order and self.user and order.user != self.user:
            raise forms.ValidationError(_('Cette commande ne vous appartient pas.'))
        return order


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
            if attachment.size > 10 * 1024 * 1024:
                raise forms.ValidationError(_('Le fichier ne doit pas dépasser 10 Mo.'))
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ]
            import mimetypes
            mime_type, _ = mimetypes.guess_type(attachment.name)
            if mime_type and mime_type not in allowed_types:
                raise forms.ValidationError(_('Type de fichier non autorisé. Formats acceptés : images, PDF, Word.'))
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
