from django.shortcuts import render, redirect
from django.utils.translation import gettext

from .demande_views import demande_view
from django.contrib import messages

from .forms import SignupForm
from .models import SignupRequest


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            from accounts.models import User, EmailVerificationToken
            from accounts.emails import send_verification_email

            user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                username=form.cleaned_data['email'],
            )
            SignupRequest.objects.create(
                user=user,
                montant=form.cleaned_data['montant'],
                duree=form.cleaned_data['duree'],
            )
            verification = EmailVerificationToken.create_for_user(user)
            send_verification_email(user, verification.token)

            messages.success(
                request,
                gettext("Votre compte a été créé. Un e-mail de vérification a été envoyé à votre adresse. "
                        "Cliquez sur le lien pour activer votre compte.")
            )
            return redirect('signup_verification_sent')
    else:
        montant = int(request.GET.get('montant', 4000))
        duree = int(request.GET.get('duree', 60))
        montant = max(100, min(250000, montant))
        duree = max(6, min(120, duree))
        form = SignupForm(initial={'montant': montant, 'duree': duree})

    montant_val = form['montant'].value() or 4000
    montant_display = f"{int(montant_val):,}".replace(',', ' ')
    duree_display = form['duree'].value() or 60

    return render(request, 'signup.html', {
        'form': form,
        'montant_display': montant_display,
        'duree_display': duree_display,
    })


def signup_success(request):
    return redirect('home')


def signup_verification_sent(request):
    """Page affichée après inscription : e-mail de vérification envoyé."""
    return render(request, 'signup_verification_sent.html')
