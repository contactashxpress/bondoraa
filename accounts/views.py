from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.utils.translation import gettext
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from .models import EmailVerificationToken, User
from .emails import send_verification_email

logger = logging.getLogger(__name__)

# ── Helpers internes ──────────────────────────────────────────────────────────

def _redirect_invalid(request, msg=None):
    """
    Redirige vers la page d'erreur de vérification.
    Utilise render() en fallback si l'URL name 'verification_invalid'
    n'est pas déclaré → évite un NoReverseMatch → 500.
    """
    if msg:
        messages.error(request, msg)
    try:
        return redirect('verification_invalid')
    except Exception:
        # L'URL name n'existe pas encore dans urls.py → on render directement
        return render(request, 'verification_invalid.html', status=400)


def _redirect_pending(request, msg=None, success=False):
    """
    Redirige vers la page en attente de vérification.
    Même protection contre NoReverseMatch.
    """
    if msg:
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    try:
        return redirect('verification_pending')
    except Exception:
        return render(request, 'verification_pending.html')


# ── Vues ──────────────────────────────────────────────────────────────────────

def verify_email(request, token):
    """Valide l'email via le token reçu par e-mail."""

    # Sécurité : le token transmis dans l'URL peut être vide ou malformé
    if not token or len(token) > 64:
        return _redirect_invalid(
            request,
            gettext("Ce lien de vérification est invalide.")
        )

    # ── Étape 1 : récupérer le token ─────────────────────────────────────────
    # uuid4().hex = 32 chars hexadécimaux → on accepte aussi les UUID avec tirets
    # DoesNotExist  : token inconnu / déjà utilisé (supprimé après validation)
    # ValueError    : token pas un UUID valide
    # ValidationError : idem selon la version Django
    # Exception     : tout autre problème DB
    try:
        verification = (
            EmailVerificationToken.objects
            .select_related('user')
            .get(token=token)
        )
    except EmailVerificationToken.DoesNotExist:
        return _redirect_invalid(
            request,
            gettext("Ce lien de vérification est invalide ou a déjà été utilisé.")
        )
    except (ValueError, ValidationError):
        logger.warning("verify_email: token malformé reçu — token=%r", token[:64])
        return _redirect_invalid(
            request,
            gettext("Ce lien de vérification est invalide.")
        )
    except Exception as e:
        logger.error("verify_email: erreur DB lors de la récupération du token — %s", e)
        return _redirect_invalid(
            request,
            gettext("Une erreur est survenue. Veuillez réessayer.")
        )

    # ── Étape 2 : vérifier que l'utilisateur existe encore ───────────────────
    # CASCADE sur le FK supprime le token si l'user est supprimé,
    # mais en cas de race condition on vérifie quand même.
    try:
        user = verification.user
        if user is None:
            raise ValueError("user est None")
    except Exception as e:
        logger.error("verify_email: user introuvable pour token=%r — %s", token, e)
        try:
            verification.delete()
        except Exception:
            pass
        return _redirect_invalid(
            request,
            gettext("Ce lien de vérification est invalide ou a expiré.")
        )

    # ── Étape 3 : vérifier l'expiration ──────────────────────────────────────
    if verification.is_expired():
        try:
            verification.delete()
        except Exception as e:
            logger.warning("verify_email: impossible de supprimer le token expiré — %s", e)
        return _redirect_invalid(
            request,
            gettext("Ce lien de vérification a expiré. Demandez un nouvel e-mail.")
        )

    # ── Étape 4 : cas déjà vérifié (double-clic sur le lien) ─────────────────
    if user.email_verified:
        try:
            verification.delete()
        except Exception:
            pass
        messages.info(request, gettext("Votre adresse e-mail est déjà validée."))
        try:
            if request.user.is_authenticated and request.user.pk == user.pk:
                return redirect('demande')
            return redirect(f"{reverse('login')}?next={reverse('demande')}")
        except Exception:
            return render(request, 'index.html')

    # ── Étape 5 : valider l'email en base (atomique) ─────────────────────────
    try:
        with transaction.atomic():
            user.email_verified = True
            user.save(update_fields=['email_verified'])  # ne réécrit qu'un champ
            verification.delete()
    except Exception as e:
        logger.error(
            "verify_email: erreur DB lors de la validation de l'user %s — %s",
            user.pk, e
        )
        return _redirect_invalid(
            request,
            gettext("Une erreur est survenue lors de la validation. Veuillez réessayer.")
        )

    # ── Étape 6 : connexion automatique ──────────────────────────────────────
    # Si le login échoue, la validation a quand même réussi :
    # on redirige vers /login/ avec un message de succès plutôt que de crasher.
    try:
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    except Exception as e:
        logger.warning(
            "verify_email: login automatique échoué pour user %s — %s",
            user.pk, e
        )
        messages.success(
            request,
            gettext("Votre adresse e-mail a été validée. Connectez-vous pour continuer.")
        )
        try:
            return redirect(f"{reverse('login')}?next={reverse('demande')}")
        except Exception:
            return render(request, 'registration/login.html')

    messages.success(request, gettext("Votre adresse e-mail a été validée. Bienvenue !"))
    try:
        return redirect('demande')
    except Exception:
        return render(request, 'index.html')


def verification_invalid(request):
    """Page affichée quand le lien de vérification est invalide ou expiré."""
    return render(request, 'verification_invalid.html')


def verification_pending(request):
    """Page pour les utilisateurs connectés mais non vérifiés."""
    if not request.user.is_authenticated:
        try:
            return redirect('login')
        except Exception:
            return render(request, 'registration/login.html')
    if request.user.email_verified:
        try:
            return redirect('demande')
        except Exception:
            return render(request, 'index.html')
    return render(request, 'verification_pending.html')


def resend_verification(request):
    """Renvoyer l'email de vérification."""
    if not request.user.is_authenticated:
        try:
            return redirect('login')
        except Exception:
            return render(request, 'registration/login.html')

    if request.user.email_verified:
        try:
            return redirect('home')
        except Exception:
            return render(request, 'index.html')

    try:
        with transaction.atomic():
            EmailVerificationToken.objects.filter(user=request.user).delete()
            verification = EmailVerificationToken.create_for_user(request.user)
        send_verification_email(request.user, verification.token)
    except Exception as e:
        logger.error(
            "resend_verification: échec pour user %s — %s",
            request.user.pk, e
        )
        return _redirect_pending(
            request,
            msg=gettext(
                "Impossible d'envoyer l'e-mail pour le moment. "
                "Veuillez réessayer plus tard."
            ),
        )

    return _redirect_pending(
        request,
        msg=gettext("Un nouvel e-mail de vérification a été envoyé."),
        success=True,
    )