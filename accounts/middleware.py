import re

from django.conf import settings
from django.shortcuts import redirect


class EmailVerificationRequiredMiddleware:
    """
    Redirige les utilisateurs connectés mais non vérifiés vers la page de vérification.
    Gère les préfixes i18n (ex: /en/verifier-email/, /de/verifier-email/).
    """
    EXEMPT_PATH_PATTERNS = [
        '/deconnexion/',
        '/verifier-email/',
        '/verification-en-attente/',
        '/renvoyer-verification/',
        '/mot-de-passe-oublie/',
        '/reset/',
        '/admin/',
        '/static/',
        '/i18n/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        # Build a regex that optionally matches a language prefix before each exempt path
        # Language prefixes look like /en/, /de/, /es/, /fr/ etc.
        lang_codes = [code for code, _ in settings.LANGUAGES]
        lang_prefix = r'(?:/(?:' + '|'.join(re.escape(c) for c in lang_codes) + r'))?'
        exempt_patterns = '|'.join(re.escape(p) for p in self.EXEMPT_PATH_PATTERNS)
        self.exempt_re = re.compile(r'^' + lang_prefix + r'(?:' + exempt_patterns + r')')

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.email_verified:
            # Staff peut accéder à l'admin
            if request.path.startswith('/admin/') and request.user.is_staff:
                return self.get_response(request)
            # Vérifier si le chemin est exempté (avec ou sans préfixe de langue)
            if self.exempt_re.match(request.path):
                return self.get_response(request)
            # Rediriger vers la page de vérification
            return redirect('verification_pending')

        return self.get_response(request)
