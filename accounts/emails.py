"""Envoi des e-mails de vérification."""
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.translation import gettext


def send_verification_email(user, token):
    """Envoie l'e-mail de vérification à l'utilisateur."""
    verify_url = f"{settings.SITE_URL.rstrip('/')}{reverse('verify_email', kwargs={'token': token})}"
    subject = gettext("Vérifiez votre adresse e-mail - Bondoraa")
    message = gettext(
        "Bonjour,\n\n"
        "Merci de vous être inscrit sur Bondoraa. Pour activer votre compte, "
        "cliquez sur le lien ci-dessous :\n\n"
        "%(verify_url)s\n\n"
        "Ce lien expire dans 24 heures.\n\n"
        "Si vous n'avez pas créé de compte, vous pouvez ignorer cet e-mail.\n\n"
        "L'équipe Bondoraa"
    ) % {"verify_url": verify_url}
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
