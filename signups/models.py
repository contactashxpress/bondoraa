import uuid
from django.conf import settings
from django.db import models
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SignupRequest(models.Model):
    """Demande d'inscription / prêt liée au visiteur."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='signup_requests',
        verbose_name=_("Utilisateur"),
        null=True,
        blank=True,
    )
    montant = models.PositiveIntegerField(help_text=_("Montant du prêt en euros"))
    duree = models.PositiveIntegerField(help_text=_("Durée en mois"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Demande de prêt")
        verbose_name_plural = _("Demandes de prêt")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.montant}€ / {self.duree} mois"


def demand_document_path(instance, filename):
    """Chemin de stockage des documents : demandes/{ref}/{type}_{filename}"""
    return f"demandes/{instance.demande.reference}/{instance.doc_type}_{filename}"


class CreditDemand(models.Model):
    """Demande de crédit complète (formulaire multi-étapes)."""
    STATUT_CHOICES = [
        ('nouvelle', _('Nouvelle')),
        ('en_cours', _("En cours d'étude")),
        ('acceptee', _('Acceptée')),
        ('refusee', _('Refusée')),
    ]
    FAMILLE_CHOICES = [
        ('celibataire', _('Célibataire')),
        ('marie', _('Marié(e)')),
        ('divorce', _('Divorcé(e)')),
    ]
    EMPLOI_CHOICES = [
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('independant', _('Indépendant')),
        ('retraite', _('Retraité(e)')),
        ('chomage', _('Sans emploi')),
        ('autre', _('Autre')),
    ]
    MOTIF_CHOICES = [
        ('travaux', _('Travaux')),
        ('auto', _('Automobile')),
        ('sante', _('Santé')),
        ('vacances', _('Vacances')),
        ('rachat', _('Rachat crédit')),
        ('autre-motif', _('Autre')),
    ]
    TYPE_ID_CHOICES = [
        ('cni', _("Carte nationale d'identité")),
        ('passeport', _('Passeport')),
        ('titre', _('Titre de séjour')),
    ]
    LOGEMENT_CHOICES = [
        ('proprio_sans', _('Propriétaire sans crédit')),
        ('proprio_avec', _('Propriétaire avec crédit')),
        ('locataire', _('Locataire')),
        ('heberge', _('Hébergé à titre gratuit')),
    ]

    reference = models.CharField(max_length=20, unique=True, db_index=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='credit_demands',
        verbose_name=_("Utilisateur"),
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='nouvelle')

    # Étape 1 - Prêt
    montant = models.PositiveIntegerField(verbose_name=_("Montant (€)"))
    duree = models.PositiveIntegerField(verbose_name=_("Durée (mois)"))

    # Étape 2 - Infos personnelles
    prenom = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    nationalite = models.CharField(max_length=50)
    email = models.EmailField()
    telephone = models.CharField(max_length=30)
    code_postal = models.CharField(max_length=10, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    situation_familiale = models.CharField(max_length=20, choices=FAMILLE_CHOICES)

    # Étape 3 - Finances
    situation_professionnelle = models.CharField(max_length=20, choices=EMPLOI_CHOICES)
    revenus_mensuels = models.PositiveIntegerField(verbose_name=_("Revenu net mensuel (€)"))
    autres_revenus = models.PositiveIntegerField(default=0, verbose_name=_("Autres revenus (€)"))
    charges_mensuelles = models.PositiveIntegerField(default=0, verbose_name=_("Charges (€)"))
    situation_logement = models.CharField(max_length=20, choices=LOGEMENT_CHOICES, blank=True)
    motif = models.CharField(max_length=20, choices=MOTIF_CHOICES, blank=True)

    # Étape 4 - Documents
    type_piece_identite = models.CharField(max_length=20, choices=TYPE_ID_CHOICES, default='cni')

    # Étape 5 - Consentements
    accepte_cgu = models.BooleanField(default=False)
    certifie_exactitude = models.BooleanField(default=False)
    accepte_marketing = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Demande de crédit")
        verbose_name_plural = _("Demandes de crédit")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.prenom} {self.nom}"

    def save(self, *args, **kwargs):
        if not self.reference:
            last_error = None
            for _ in range(10):
                self.reference = self._generate_reference()
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError as e:
                    last_error = e
                    self.reference = None
            raise last_error
        super().save(*args, **kwargs)

    def _generate_reference(self):
        year = timezone.now().year
        return f"BD-{year}-{uuid.uuid4().hex[:8].upper()}"


class DemandProcessStep(models.Model):
    """
    Catalogue des étapes du parcours (modifiable en admin).
    Chaque nouvelle demande crée une ligne CreditDemandStepStatus par étape active.
    """
    order = models.PositiveSmallIntegerField(default=0, db_index=True)
    code = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=200, verbose_name=_("Titre"))
    description = models.TextField(
        blank=True,
        verbose_name=_("Description client"),
        help_text=_("Texte affiché au demandeur sous le titre de l'étape."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Si coché, l'étape est utilisée pour les nouvelles demandes."),
    )

    class Meta:
        verbose_name = _("Étape du processus")
        verbose_name_plural = _("Étapes du processus")
        ordering = ["order", "pk"]

    def __str__(self):
        return f"{self.order}. {self.title}"


class CreditDemandStepStatus(models.Model):
    """État d'avancement d'une demande pour une étape donnée."""

    STATUT_ETAPE_CHOICES = [
        ("pending", _("En attente")),
        ("in_progress", _("En cours")),
        ("completed", _("Terminée")),
    ]

    demande = models.ForeignKey(
        CreditDemand,
        on_delete=models.CASCADE,
        related_name="step_statuses",
    )
    step = models.ForeignKey(
        DemandProcessStep,
        on_delete=models.PROTECT,
        related_name="demand_statuses",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUT_ETAPE_CHOICES,
        default="pending",
        verbose_name=_("État"),
    )
    client_message = models.TextField(
        blank=True,
        verbose_name=_("Message au client"),
        help_text=_("Optionnel : précision visible sur la page « Ma demande »."),
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Suivi d'étape")
        verbose_name_plural = _("Suivis d'étapes")
        ordering = ["step__order", "step__pk"]
        constraints = [
            models.UniqueConstraint(fields=["demande", "step"], name="unique_demande_step"),
        ]

    def __str__(self):
        return f"{self.demande.reference} — {self.step.title}"


class DemandDocument(models.Model):
    """Document joint à une demande de crédit."""
    DOC_TYPE_CHOICES = [
        ('id_recto', _("Pièce d'identité recto")),
        ('id_verso', _("Pièce d'identité verso")),
        ('revenus', _('Justificatif de revenus')),
        ('domicile', _('Justificatif de domicile')),
    ]

    demande = models.ForeignKey(
        CreditDemand,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    fichier = models.FileField(upload_to=demand_document_path, max_length=255)

    class Meta:
        verbose_name = _("Document de demande")
        verbose_name_plural = _("Documents de demande")
