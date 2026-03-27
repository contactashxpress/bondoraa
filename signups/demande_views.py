"""Vues pour le formulaire de demande de crédit."""
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods

from config.file_validation import DOCUMENT_PRESET
from config.secure_upload import process_demand_upload

from .emails import send_demande_recue_email
from .forms import CreditDemandForm
from .models import CreditDemand, DemandDocument, SignupRequest
from .services import init_step_statuses_for_demand

logger = logging.getLogger(__name__)

_SLIDER_MONTANT = (100, 250_000)
_SLIDER_DUREE = (6, 120)


def _pct_slider(val, min_v, max_v):
    if max_v <= min_v:
        return 0
    return round((val - min_v) / (max_v - min_v) * 100, 2)


def _initial_montant_duree(user, has_credit_demand):
    """
    Préremplit depuis SignupRequest si aucune demande de crédit enregistrée.
    Retourne ((montant, duree), prefill_from_signup).
    """
    defaults = (4000, 60)
    if has_credit_demand:
        return defaults, False
    sr = SignupRequest.objects.filter(user=user).order_by("-created_at").first()
    if not sr:
        return defaults, False
    lo, hi = _SLIDER_MONTANT
    montant = max(lo, min(hi, sr.montant))
    montant = (montant // 100) * 100
    lo_d, hi_d = _SLIDER_DUREE
    duree = max(lo_d, min(hi_d, sr.duree))
    duree = (duree // 6) * 6
    return (montant, duree), True


@login_required(login_url='signup')
@require_http_methods(["GET", "POST"])
def demande_view(request):
    """Affiche le formulaire ou traite la soumission."""
    if request.method == "GET":
        demandes = CreditDemand.objects.filter(user=request.user).order_by("-created_at")
        suivi_demande = demandes.first()
        etapes_suivi = []
        autres_demandes = []
        if suivi_demande:
            if not suivi_demande.step_statuses.exists():
                init_step_statuses_for_demand(suivi_demande)
            etapes_suivi = list(
                suivi_demande.step_statuses.select_related("step").order_by(
                    "step__order", "step__pk"
                )
            )
            if demandes.count() > 1:
                autres_demandes = list(demandes[1:6])

        has_credit = demandes.exists()
        (initial_montant, initial_duree), prefill_from_signup = _initial_montant_duree(
            request.user, has_credit
        )
        start_step = 2 if prefill_from_signup else 1

        return render(
            request,
            "demande.html",
            {
                "suivi_demande": suivi_demande,
                "etapes_suivi": etapes_suivi,
                "autres_demandes": autres_demandes,
                "initial_montant": initial_montant,
                "initial_duree": initial_duree,
                "pct_montant": _pct_slider(initial_montant, *_SLIDER_MONTANT),
                "pct_duree": _pct_slider(initial_duree, *_SLIDER_DUREE),
                "prefill_from_signup": prefill_from_signup,
                "start_step": start_step,
            },
        )

    # POST : soumission AJAX
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": gettext("Requête invalide")}, status=400)

    try:
        data = request.POST
        files = request.FILES

        # Validation des champs obligatoires
        form_data = {
            "montant": int(data.get("montant", 0) or 0),
            "duree": int(data.get("duree", 0) or 0),
            "prenom": data.get("prenom", "").strip(),
            "nom": data.get("nom", "").strip(),
            "date_naissance": data.get("naissance") or None,
            "nationalite": data.get("nationalite", "").strip(),
            "email": data.get("email", "").strip(),
            "telephone": data.get("tel", "").strip(),
            "code_postal": data.get("code_postal", "").strip(),
            "adresse": data.get("adresse", "").strip(),
            "situation_familiale": data.get("famille", ""),
            "situation_professionnelle": data.get("emploi", ""),
            "revenus_mensuels": int(data.get("revenus", 0) or 0),
            "autres_revenus": int(data.get("autres_revenus", 0) or 0),
            "charges_mensuelles": int(data.get("charges", 0) or 0),
            "situation_logement": data.get("logement", ""),
            "motif": data.get("motif", ""),
            "type_piece_identite": data.get("type_id", "cni"),
            "accepte_cgu": data.get("cgu") == "on" or data.get("cgu") == "true",
            "certifie_exactitude": data.get("exacts") == "on" or data.get("exacts") == "true",
            "accepte_marketing": data.get("marketing") == "on" or data.get("marketing") == "true",
        }

        form = CreditDemandForm(data=form_data)
        if not form.is_valid():
            errors = {k: v[0] for k, v in form.errors.items()}
            return JsonResponse({"success": False, "errors": errors}, status=400)

        # Documents obligatoires
        id_recto = files.getlist("id_recto")
        id_verso = files.getlist("id_verso")
        revenus = files.getlist("revenus")
        domicile = files.getlist("domicile")

        if not id_recto or len(id_recto) == 0:
            return JsonResponse(
                {"success": False, "errors": {"id_recto": gettext("Pièce d'identité recto requise")}},
                status=400,
            )
        if not revenus or len(revenus) == 0:
            return JsonResponse(
                {"success": False, "errors": {"revenus": gettext("Justificatif de revenus requis")}},
                status=400,
            )

        # Validation sécurisée des fichiers (MIME, extension, taille)
        field_labels = {
            "id_recto": gettext("Pièce d'identité recto"),
            "id_verso": gettext("Pièce d'identité verso"),
            "revenus": gettext("Justificatif de revenus"),
            "domicile": gettext("Justificatif de domicile"),
        }
        processed_docs = []
        for field_key, file_list in [
            ("id_recto", id_recto),
            ("id_verso", id_verso),
            ("revenus", revenus),
            ("domicile", domicile),
        ]:
            for f in file_list:
                content_file, err = process_demand_upload(
                    f, DOCUMENT_PRESET, field_labels[field_key]
                )
                if err:
                    return JsonResponse(
                        {"success": False, "errors": {field_key: err}},
                        status=400,
                    )
                processed_docs.append((field_key, content_file))

        # Créer la demande (sans sauvegarder pour avoir la ref)
        demande_obj = form.save(commit=False)
        demande_obj.user = request.user
        demande_obj.save()

        # Enregistrer les documents (fichiers normalisés, noms uuid)
        for doc_type_key, content_file in processed_docs:
            DemandDocument.objects.create(
                demande=demande_obj, doc_type=doc_type_key, fichier=content_file
            )

        sr = SignupRequest.objects.filter(user=request.user).order_by("-created_at").first()
        if sr:
            sr.montant = demande_obj.montant
            sr.duree = demande_obj.duree
            sr.save(update_fields=["montant", "duree"])

        init_step_statuses_for_demand(demande_obj)

        try:
            send_demande_recue_email(demande_obj)
        except Exception:
            logger.exception(
                "Échec envoi e-mail confirmation demande (réf. %s, user_id=%s)",
                demande_obj.reference,
                request.user.pk,
            )

        return JsonResponse(
            {"success": True, "reference": demande_obj.reference},
            status=201,
        )

    except (ValueError, KeyError) as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )
