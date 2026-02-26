from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.utils.translation import gettext

from .models import EmailVerificationToken, User
from .emails import send_verification_email


def verify_email(request, token):
    """Valide l'email via le token reçu par e-mail."""
    try:
        verification = EmailVerificationToken.objects.get(token=token)
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, gettext("Ce lien de vérification est invalide ou a expiré."))
        return redirect('verification_invalid')

    if verification.is_expired():
        verification.delete()
        messages.error(request, gettext("Ce lien de vérification a expiré. Demandez un nouvel e-mail."))
        return redirect('verification_invalid')

    user = verification.user
    user.email_verified = True
    user.save()
    verification.delete()

    login(request, user)
    messages.success(request, gettext("Votre adresse e-mail a été validée. Bienvenue !"))
    return redirect('home')


def verification_invalid(request):
    """Page affichée quand le lien de vérification est invalide."""
    return render(request, 'verification_invalid.html')


def verification_pending(request):
    """Page pour les utilisateurs connectés mais non vérifiés."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.email_verified:
        return redirect('home')
    return render(request, 'verification_pending.html')


def resend_verification(request):
    """Renvoyer l'email de vérification."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.email_verified:
        return redirect('home')

    # Supprimer les anciens tokens
    EmailVerificationToken.objects.filter(user=request.user).delete()

    verification = EmailVerificationToken.create_for_user(request.user)
    send_verification_email(request.user, verification.token)

    messages.success(request, gettext("Un nouvel e-mail de vérification a été envoyé."))
    return redirect('verification_pending')
