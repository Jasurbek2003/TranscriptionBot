from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin configuration for wallets"""

    list_display = [
        "id",
        "user_info",
        "balance_display",
        "currency",
        "status_badge",
        "total_credited",
        "total_debited",
        "last_transaction_at",
        "created_at",
    ]

    list_filter = ["currency", "is_active", "created_at", "last_transaction_at"]

    search_fields = [
        "user__telegram_id",
        "user__telegram_username",
        "user__first_name",
        "user__last_name",
    ]

    readonly_fields = [
        "total_credited",
        "total_debited",
        "created_at",
        "updated_at",
        "last_transaction_at",
    ]

    fieldsets = (
        (_("Wallet Info"), {"fields": ("user", "balance", "currency", "is_active")}),
        (_("Limits"), {"fields": ("daily_limit", "monthly_limit")}),
        (_("Statistics"), {"fields": ("total_credited", "total_debited", "last_transaction_at")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    ordering = ["-created_at"]

    @admin.display(description=_("User"))
    def user_info(self, obj):
        """Display user info"""
        return format_html(
            '<a href="/admin/users/telegramuser/{}/change/">{}</a>', obj.user.id, obj.user
        )

    @admin.display(description=_("Balance"))
    def balance_display(self, obj):
        """Display balance with color"""
        color = "green" if obj.balance > 0 else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, obj.balance
        )

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        """Display status as badge"""
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; '
                'padding: 3px 8px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: red; color: white; '
            'padding: 3px 8px; border-radius: 3px;">Inactive</span>'
        )

    actions = ["activate_wallets", "deactivate_wallets", "add_bonus"]

    @admin.action(description=_("Activate selected wallets"))
    def activate_wallets(self, request, queryset):
        """Activate selected wallets"""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} wallets activated.")

    @admin.action(description=_("Deactivate selected wallets"))
    def deactivate_wallets(self, request, queryset):
        """Deactivate selected wallets"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} wallets deactivated.")

    @admin.action(description=_("Add 100 UZS bonus"))
    def add_bonus(self, request, queryset):
        """Add bonus to selected wallets"""
        from decimal import Decimal

        bonus_amount = Decimal("100.00")  # Fixed bonus amount

        for wallet in queryset:
            wallet.add_balance(bonus_amount, "Admin bonus")

        self.message_user(
            request, f"Added {bonus_amount} {wallet.currency} bonus to {queryset.count()} wallets."
        )
