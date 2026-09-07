from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Order


class CheckoutForm(forms.Form):
    fulfillment_type = forms.ChoiceField(
        choices=Order.FulfillmentType.choices,
        widget=forms.RadioSelect(),
        initial=Order.FulfillmentType.PICKUP,
    )
    delivery_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': _('Full delivery address')}),
    )
    delivery_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': _('Special instructions')}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': _('Order notes')}),
    )
    vehicle = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label=_('Select a vehicle (optional)'),
        widget=forms.Select(attrs={'class': 'form-input'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['vehicle'].queryset = user.vehicles.all()


class OrderCancelForm(forms.Form):
    cancel_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': _('Reason for cancellation')}),
    )
