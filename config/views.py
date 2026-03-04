from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language


def home(request):
    """Affiche la page d'accueil."""
    return render(request, 'index.html')


def set_language(request):
    """
    Custom language switcher view compatible with Django 6.0.

    - Reads the target language from POST param 'language'
    - Stores it in the language cookie
    - Redirects to the language-prefixed version of the 'next' URL
      using translate_url() so that LocaleMiddleware detects it
      from the URL prefix on the next request.
    """
    next_url = request.POST.get('next', request.GET.get('next'))

    # Validate the next URL
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = '/'

    if request.method == 'POST':
        lang_code = request.POST.get('language')

        if lang_code and check_for_language(lang_code):
            # Translate the URL to include the proper language prefix
            # e.g. '/' stays '/' for French (default), becomes '/en/' for English
            next_trans = translate_url(next_url, lang_code)
            if next_trans != next_url:
                next_url = next_trans

            response = HttpResponseRedirect(next_url)

            # Store in the language cookie (this is how Django 6.0 does it)
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
            return response

    return HttpResponseRedirect(next_url)