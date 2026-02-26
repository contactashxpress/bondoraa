from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailOrUsernameBackend(ModelBackend):
    """Authentification par email ou identifiant (username)."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None or password is None:
            return None

        # Chercher par email ou username
        if '@' in username:
            user = User.objects.filter(email__iexact=username).first()
        else:
            user = User.objects.filter(username__iexact=username).first()
            if user is None:
                user = User.objects.filter(email__iexact=username).first()

        if user and user.check_password(password):
            return user
        return None
