from django.contrib import admin
from .models import CreditDemand, DemandDocument, SignupRequest


@admin.register(SignupRequest)
class SignupRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'montant', 'duree', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)


class DemandDocumentInline(admin.TabularInline):
    model = DemandDocument
    extra = 0


@admin.register(CreditDemand)
class CreditDemandAdmin(admin.ModelAdmin):
    list_display = ('reference', 'prenom', 'nom', 'email', 'montant', 'duree', 'statut', 'created_at')
    list_filter = ('statut', 'created_at')
    search_fields = ('reference', 'prenom', 'nom', 'email')
    inlines = [DemandDocumentInline]
