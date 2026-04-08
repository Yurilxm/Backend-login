from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin personalizado para User model"""
    
    list_display = ['email', 'username', 'first_name', 'last_name', 'is_active', 'is_2fa_enabled', 'created_at']
    list_filter = ['is_active', 'is_2fa_enabled', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('2FA Info'), {'fields': ('is_2fa_enabled', 'two_factor_secret')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    actions = ['activate_users', 'deactivate_users']
    
    def activate_users(self, request, queryset):
        """Ação para ativar usuários em lote"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} usuário(s) ativado(s) com sucesso.')
    activate_users.short_description = 'Ativar usuários selecionados'
    
    def deactivate_users(self, request, queryset):
        """Ação para desativar usuários em lote"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} usuário(s) desativado(s) com sucesso.')
    deactivate_users.short_description = 'Desativar usuários selecionados'

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve save_model para garantir que update_fields seja usado
        """
        if change and 'is_active' in form.changed_data:
            obj.save(update_fields=['is_active'])
        else:
            obj.save()