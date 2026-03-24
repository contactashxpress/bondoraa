"""Logique métier des demandes de crédit."""
from django.db import transaction
from django.utils import timezone

from .models import CreditDemand, CreditDemandStepStatus, DemandProcessStep


def init_step_statuses_for_demand(demande: CreditDemand) -> None:
    """
    Crée une ligne de suivi pour chaque étape active du processus.
    L'état initial dépend du statut global de la demande (nouvelle, en cours, terminée).
    """
    steps = list(DemandProcessStep.objects.filter(is_active=True).order_by("order", "pk"))
    if not steps:
        return
    if CreditDemandStepStatus.objects.filter(demande=demande).exists():
        return

    statut = demande.statut
    now = timezone.now()

    for i, step in enumerate(steps):
        if statut in ("acceptee", "refusee"):
            st = "completed"
            completed_at = now
        elif statut == "en_cours":
            if i == 0:
                st, completed_at = "completed", now
            elif i == 1:
                st, completed_at = "in_progress", None
            else:
                st, completed_at = "pending", None
        else:  # nouvelle
            if i == 0:
                st, completed_at = "completed", now
            elif i == 1:
                st, completed_at = "in_progress", None
            else:
                st, completed_at = "pending", None

        CreditDemandStepStatus.objects.create(
            demande=demande,
            step=step,
            status=st,
            completed_at=completed_at,
        )


def sync_steps_from_global_status(demande: CreditDemand) -> None:
    """
    Recalcule les étapes lorsque le statut global change (depuis l'admin).
    """
    steps = list(
        CreditDemandStepStatus.objects.filter(demande=demande)
        .select_related("step")
        .order_by("step__order", "step__pk")
    )
    if not steps:
        init_step_statuses_for_demand(demande)
        return

    statut = demande.statut
    now = timezone.now()

    with transaction.atomic():
        if statut in ("acceptee", "refusee"):
            for row in steps:
                row.status = "completed"
                row.completed_at = row.completed_at or now
                row.save(update_fields=["status", "completed_at", "updated_at"])
        elif statut == "en_cours":
            for j, row in enumerate(steps):
                if j == 0:
                    row.status = "completed"
                    row.completed_at = row.completed_at or now
                elif j == 1:
                    row.status = "in_progress"
                    row.completed_at = None
                else:
                    row.status = "pending"
                    row.completed_at = None
                row.save(update_fields=["status", "completed_at", "updated_at"])
        else:  # nouvelle
            for j, row in enumerate(steps):
                if j == 0:
                    row.status = "completed"
                    row.completed_at = row.completed_at or now
                elif j == 1:
                    row.status = "in_progress"
                    row.completed_at = None
                else:
                    row.status = "pending"
                    row.completed_at = None
                row.save(update_fields=["status", "completed_at", "updated_at"])
