from django.shortcuts import redirect
from django.urls import reverse


class EmailVerificationRequiredMiddleware:
    """
    Redirige les utilisateurs connectés mais non vérifiés vers la page de vérification.
    """
    EXEMPT_PREFIXES = [
        '/deconnexion/',
        '/verifier-email/',
        '/verification-en-attente/',
        '/renvoyer-verification/',
        '/mot-de-passe-oublie/',
        '/reset/',
        '/admin/',
        '/static/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.email_verified:
            # Staff peut accéder à l'admin
            if request.path.startswith('/admin/') and request.user.is_staff:
                return self.get_response(request)
            # Vérifier si le chemin est exempté
            for prefix in self.EXEMPT_PREFIXES:
                if request.path.startswith(prefix):
                    return self.get_response(request)
            # Rediriger vers la page de vérification
            return redirect('verification_pending')

        return self.get_response(request)
