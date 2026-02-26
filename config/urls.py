"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from accounts import views as account_views
from config import views
from signups import views as signup_views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
]

urlpatterns += i18n_patterns(
    path('', views.home, name='home'),
    path('demande/', signup_views.demande_view, name='demande'),
    path('inscription/', signup_views.signup, name='signup'),
    path('inscription/verification-envoyee/', signup_views.signup_verification_sent, name='signup_verification_sent'),
    path('inscription/succes/', signup_views.signup_success, name='signup_success'),
    path('verifier-email/<str:token>/', account_views.verify_email, name='verify_email'),
    path('verification-en-attente/', account_views.verification_pending, name='verification_pending'),
    path('verification-invalide/', account_views.verification_invalid, name='verification_invalid'),
    path('renvoyer-verification/', account_views.resend_verification, name='resend_verification'),
    path('connexion/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('deconnexion/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('mot-de-passe-oublie/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
    ), name='password_reset'),
    path('mot-de-passe-oublie/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
