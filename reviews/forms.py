from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'photo']
        widgets = {
            'rating': forms.HiddenInput(attrs={'id': 'rating-input'}),
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Summary (optional)')}),
            'comment': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': _('Your review...')}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-input'}),
        }


class ReviewReplyForm(forms.Form):
    professional_reply = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
    )
