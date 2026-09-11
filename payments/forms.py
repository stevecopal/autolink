from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Payment


class PaymentForm(forms.Form):
    provider = forms.ChoiceField(
        choices=[(c, l) for c, l in Payment.Provider.choices],
        widget=forms.RadioSelect(),
    )
    phone_number = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+237 6XX XXX XXX',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get('provider')
        phone = cleaned.get('phone_number')
        if provider in ('MTN_MOMO', 'ORANGE_MONEY') and not phone:
            self.add_error('phone_number', _('Phone number is required for mobile money.'))
        return cleaned


class RefundRequestForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
    )
