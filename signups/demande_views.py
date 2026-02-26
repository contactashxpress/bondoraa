"""Vues pour le formulaire de demande de crédit."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods

from .forms import CreditDemandForm
from .models import CreditDemand, DemandDocument


@login_required(login_url='signup')
@require_http_methods(["GET", "POST"])
def demande_view(request):
    """Affiche le formulaire ou traite la soumission."""
    if request.method == "GET":
        return render(request, "demande.html")

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

        # Signature (base64)
        signature = data.get("signature", "").strip()
        if signature and signature.startswith("data:image"):
            # Garder uniquement la partie base64 si besoin
            form_data["signature"] = signature
        else:
            form_data["signature"] = signature or ""

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

        # Créer la demande (sans sauvegarder pour avoir la ref)
        demande_obj = form.save(commit=False)
        demande_obj.user = request.user
        demande_obj.signature = form_data.get("signature", "")
        demande_obj.save()

        # Enregistrer les documents
        for f in id_recto:
            DemandDocument.objects.create(demande=demande_obj, doc_type="id_recto", fichier=f)
        for f in id_verso:
            DemandDocument.objects.create(demande=demande_obj, doc_type="id_verso", fichier=f)
        for f in revenus:
            DemandDocument.objects.create(demande=demande_obj, doc_type="revenus", fichier=f)
        for f in domicile:
            DemandDocument.objects.create(demande=demande_obj, doc_type="domicile", fichier=f)

        return JsonResponse(
            {"success": True, "reference": demande_obj.reference},
            status=201,
        )

    except (ValueError, KeyError) as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )
