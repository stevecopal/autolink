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


class ReviewCreateForm(forms.Form):
    """Form for creating a review tied to a completed order."""
    rating = forms.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        widget=forms.HiddenInput(attrs={'id': 'rating-input'}),
    )
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Résumé (optionnel)'),
        }),
    )
    comment = forms.CharField(
        min_length=10,
        max_length=2000,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': _('Décrivez votre expérience...'),
        }),
    )

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None and (rating < 1 or rating > 5):
            raise forms.ValidationError(_('La note doit être comprise entre 1 et 5.'))
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if len(comment) < 10:
            raise forms.ValidationError(
                _('Le commentaire doit contenir au moins 10 caractères.')
            )
        return comment


class ReviewReplyForm(forms.Form):
    professional_reply = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
    )
