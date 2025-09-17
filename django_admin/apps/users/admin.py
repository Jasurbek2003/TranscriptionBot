from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Sum
from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(BaseUserAdmin):
    """Admin configuration for Telegram users"""

    list_display = [
        'telegram_id',
        'telegram_username_link',
        'full_name',
        'role_badge',
        'status_badge',
        'wallet_balance',
        'total_transcriptions',
        'created_at'
    ]

    list_filter = [
        'status',
        'role',
        'language_code',
        'is_premium',
        'is_bot',
        'created_at'
    ]

    search_fields = [
        'telegram_id',
        'telegram_username',
        'first_name',
        'last_name',
        'phone_number',
        'email'
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'last_activity',
        'total_transcriptions',
        'total_spent',
        'wallet_balance',
        'username',
    ]

    fieldsets = (
        (_('Telegram Info'), {
            'fields': ('username','telegram_id', 'telegram_username', 'is_bot', 'is_premium')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'language_code')
        }),
        (_('Permissions'), {
            'fields': ('role', 'status', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Activity'), {
            'fields': ('last_activity', 'total_transcriptions', 'total_spent')
        }),
        (_('Settings'), {
            'fields': ('notifications_enabled', 'metadata')
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
        (_('Ballance'), {
         'fields': ('wallet_balance',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('telegram_id', 'telegram_username', 'first_name', 'password1', 'password2'),
        }),
    )

    ordering = ['-created_at']

    def telegram_username_link(self, obj):
        """Display Telegram username as link"""
        if obj.telegram_username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank">@{}</a>',
                obj.telegram_username,
                obj.telegram_username
            )
        return '-'

    telegram_username_link.short_description = _('Username')

    def full_name(self, obj):
        """Display full name"""
        return obj.full_name or '-'

    full_name.short_description = _('Full Name')

    def role_badge(self, obj):
        """Display role as badge"""
        colors = {
            'user': 'gray',
            'moderator': 'blue',
            'admin': 'orange',
            'super_admin': 'red'
        }
        color = colors.get(obj.role, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_role_display()
        )

    role_badge.short_description = _('Role')

    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'active': 'green',
            'inactive': 'gray',
            'blocked': 'red',
            'deleted': 'black'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = _('Status')

    def wallet_balance(self, obj):
        """Display wallet balance"""
        try:
            wallet = obj.wallet
            return format_html(
                '<span style="font-weight: bold;">{:,.2f} UZS</span>',
                wallet.balance
            )
        except:
            return '-'

    wallet_balance.short_description = _('Balance')

    actions = ['block_users', 'unblock_users', 'export_to_csv']

    def block_users(self, request, queryset):
        """Block selected users"""
        count = queryset.update(status='blocked')
        self.message_user(request, f'{count} users blocked.')

    block_users.short_description = _('Block selected users')

    def unblock_users(self, request, queryset):
        """Unblock selected users"""
        count = queryset.update(status='active')
        self.message_user(request, f'{count} users unblocked.')

    unblock_users.short_description = _('Unblock selected users')