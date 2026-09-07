from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User
from core.models import City


class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Ex: +237 6XX XXX XXX'
        })
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True),
        required=True,
        empty_label='Choisir une ville',
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    neighborhood = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Ex: Bonamoussadi'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'city', 'neighborhood', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Votre nom d\'utilisateur'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'votre@email.com'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Mot de passe'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirmer le mot de passe'
        })
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        for field_name in self.fields:
            self.fields[field_name].help_text = ''


class CustomLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].help_text = ''
        self.fields['username'].widget = forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nom d\'utilisateur',
            'autofocus': True
        })
        self.fields['password'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Mot de passe'
        })


class UserProfileForm(forms.ModelForm):
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True),
        required=False,
        empty_label='Choisir une ville',
        widget=forms.Select(attrs={'class': 'form-input'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'city', 'neighborhood', 'address', 'whatsapp', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Nom'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Téléphone'}),
            'neighborhood': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Quartier'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Adresse'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Numéro WhatsApp'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].help_text = ''
