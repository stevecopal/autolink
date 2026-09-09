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
        label=_("Preuve (optionnel)"),
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-input",
                "accept": "image/*,application/pdf,.doc,.docx",
            }
        ),
    )

    class Meta:
        model = Ticket
        fields = [
            "subject",
            "description",
            "garage",
            "evidence",
        ]  # order et part retirés
        widgets = {
            "subject": forms.TextInput(
                attrs={
                    "class": "form-input w-full",
                    "placeholder": _("Ex: Garage frauduleux"),
                    "maxlength": 300,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input w-full",
                    "rows": 4,
                    "placeholder": _("Décrivez votre problème en détail..."),
                }
            ),
            "garage": forms.Select(
                attrs={
                    "class": "form-input w-full",
                    "id": "ticket-garage",
                }
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user:
            from garages.models import Garage

            # Filtrer les garages approuvés, actifs et visibles
            self.fields["garage"].queryset = Garage.objects.filter(
                approval_status=Garage.ApprovalStatus.APPROVED,
                activation_status=Garage.ActivationStatus.ACTIVE,
                is_active=True,
            ).order_by("name")
            # Rendre garage obligatoire
            self.fields["garage"].required = True
        else:
            self.fields["garage"].queryset = Garage.objects.none()

    def clean_evidence(self):
        evidence = self.cleaned_data.get("evidence")
        if evidence:
            if evidence.size > MAX_FILE_SIZE:
                raise ValidationError(
                    _("Le fichier ne doit pas dépasser %(size)s Mo.") % {"size": 5}
                )
            mime_type, _ = mimetypes.guess_type(evidence.name)
            if mime_type and mime_type not in ALLOWED_MIME_TYPES:
                raise ValidationError(
                    _(
                        "Type de fichier non autorisé. Formats acceptés : images (JPG, PNG, GIF, WebP), PDF, Word."
                    )
                )
            ext = os.path.splitext(evidence.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    _("Extension non autorisée. Formats acceptés : %(formats)s.")
                    % {"formats": ", ".join(ALLOWED_EXTENSIONS)}
                )
        return evidence
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
