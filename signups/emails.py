"""E-mails liés aux demandes de crédit."""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext

from .models import CreditDemand

logger = logging.getLogger(__name__)


def send_demande_recue_email(demande: CreditDemand) -> None:
    """
    Informe l'utilisateur que sa demande de prêt a bien été reçue et sera traitée sous peu.
    Lève une exception si l'envoi échoue (à gérer par l'appelant si besoin).
    """
    user = demande.user
    site_url = settings.SITE_URL.rstrip("/")
    reference = demande.reference
    prenom = demande.prenom

    subject = gettext("Votre demande de prêt a bien été reçue — Bondoraa")

    message = gettext(
        "Bonjour %(prenom)s,\n\n"
        "Nous avons bien reçu votre demande de prêt sur Bondoraa.\n\n"
        "Référence de votre dossier : %(reference)s\n"
        "Montant demandé : %(montant)s €\n"
        "Durée : %(duree)s mois\n\n"
        "Notre équipe va l'examiner et vous recontactera dans les meilleurs délais.\n\n"
        "Merci de votre confiance.\n\n"
        "L'équipe Bondoraa"
    ) % {
        "prenom": prenom,
        "reference": reference,
        "montant": f"{demande.montant:,}".replace(",", " "),
        "duree": demande.duree,
    }

    html_message = render_to_string(
        "emails/demande_recue_email.html",
        {
            "demande": demande,
            "site_url": site_url,
        },
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
