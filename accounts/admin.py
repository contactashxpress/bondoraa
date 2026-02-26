from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'email_verified', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('email_verified', 'is_staff', 'is_active')
    search_fields = ('email',)
    ordering = ('-date_joined',)
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Vérification', {'fields': ('email_verified',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'token')

    def email(self, obj):
        return obj.user.email
    email.short_description = 'E-mail'
