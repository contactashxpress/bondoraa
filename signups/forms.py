from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import CreditDemand

User = get_user_model()


class SignupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control js-email-field',
            'placeholder': _('E-mail'),
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Mot de passe'),
            'autocomplete': 'new-password',
        }),
        label=_("Mot de passe")
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirmer le mot de passe'),
            'autocomplete': 'new-password',
        }),
        label=_("Confirmer le mot de passe")
    )
    montant = forms.IntegerField(
        min_value=100,
        max_value=250000,
        widget=forms.HiddenInput()
    )
    duree = forms.IntegerField(
        min_value=6,
        max_value=120,
        widget=forms.HiddenInput()
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Un compte existe déjà avec cette adresse e-mail."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError(_("Les deux mots de passe ne correspondent pas."))
        return cleaned_data


class CreditDemandForm(forms.ModelForm):
    """Formulaire de validation pour une demande de crédit."""

    class Meta:
        model = CreditDemand
        exclude = ('reference', 'user', 'statut', 'created_at')
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_montant(self):
        val = self.cleaned_data.get('montant')
        if val is not None and (val < 100 or val > 250000):
            raise ValidationError(_("Le montant doit être entre 100 € et 250 000 €."))
        return val

    def clean_duree(self):
        val = self.cleaned_data.get('duree')
        if val is not None and (val < 6 or val > 120):
            raise ValidationError(_("La durée doit être entre 6 et 120 mois."))
        return val

    def clean_date_naissance(self):
        val = self.cleaned_data.get('date_naissance')
        if val:
            today = date.today()
            age = (today - val).days / 365.25
            if age < 18:
                raise ValidationError(_("Vous devez avoir au moins 18 ans."))
        return val
