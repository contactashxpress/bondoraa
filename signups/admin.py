from django.contrib import admin

from .models import (
    CreditDemand,
    CreditDemandStepStatus,
    DemandDocument,
    DemandProcessStep,
    SignupRequest,
)
from .services import init_step_statuses_for_demand, sync_steps_from_global_status


@admin.register(SignupRequest)
class SignupRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'montant', 'duree', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email',)


class DemandDocumentInline(admin.TabularInline):
    model = DemandDocument
    extra = 0


class CreditDemandStepStatusInline(admin.TabularInline):
    model = CreditDemandStepStatus
    extra = 0
    can_delete = False
    ordering = ('step__order', 'step__pk')
    readonly_fields = ('step', 'updated_at')
    fields = ('step', 'status', 'client_message', 'completed_at', 'updated_at')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditDemand)
class CreditDemandAdmin(admin.ModelAdmin):
    list_display = ('reference', 'prenom', 'nom', 'email', 'montant', 'duree', 'statut', 'created_at')
    list_filter = ('statut', 'created_at')
    search_fields = ('reference', 'prenom', 'nom', 'email')
    inlines = [CreditDemandStepStatusInline, DemandDocumentInline]
    readonly_fields = ('reference', 'created_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            init_step_statuses_for_demand(obj)
        elif change and 'statut' in form.changed_data:
            sync_steps_from_global_status(obj)


@admin.register(DemandProcessStep)
class DemandProcessStepAdmin(admin.ModelAdmin):
    list_display = ('order', 'code', 'title', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'title')
    ordering = ('order', 'pk')
