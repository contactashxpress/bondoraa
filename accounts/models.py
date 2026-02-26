import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse e-mail est requise."))
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Utilisateur avec email comme identifiant principal."""
    email = models.EmailField(unique=True, blank=False)
    email_verified = models.BooleanField(default=False, verbose_name=_("E-mail vérifié"))
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")


class EmailVerificationToken(models.Model):
    """Token pour la validation d'email (expire après 24h)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Token de vérification e-mail")
        verbose_name_plural = _("Tokens de vérification e-mail")

    @classmethod
    def create_for_user(cls, user):
        token = uuid.uuid4().hex
        return cls.objects.create(user=user, token=token)

    def is_expired(self, max_age_hours=24):
        return timezone.now() > self.created_at + timedelta(hours=max_age_hours)
