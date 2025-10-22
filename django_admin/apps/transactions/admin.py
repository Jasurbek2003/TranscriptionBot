from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin configuration for transactions"""

    list_display = [
        "reference_id_short",
        "user_link",
        "type_badge",
        "amount_display",
        "payment_method",
        # 'gateway_badge',
        "status_badge",
        "created_at",
    ]

    list_filter = ["type", "status", "payment_method", "gateway", "created_at"]

    search_fields = [
        "reference_id",
        "external_id",
        "gateway_transaction_id",
        "user__telegram_id",
        "user__telegram_username",
        "description",
    ]

    readonly_fields = [
        "reference_id",
        "balance_before",
        "balance_after",
        "processed_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Transaction Info"),
            {"fields": ("user", "wallet", "type", "amount", "balance_before", "balance_after")},
        ),
        (
            _("Payment Details"),
            {
                "fields": (
                    "payment_method",
                    "gateway",
                    "status",
                    "reference_id",
                    "external_id",
                    "gateway_transaction_id",
                    "processed_at",
                    "failed_reason",
                )
            },
        ),
        (_("Related Object"), {"fields": ("related_object_type", "related_object_id")}),
        (_("Additional Info"), {"fields": ("description", "metadata")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    @admin.display(description=_("Ref ID"))
    def reference_id_short(self, obj):
        """Display shortened reference ID"""
        return f"...{str(obj.reference_id)[-8:]}"

    @admin.display(description=_("User"))
    def user_link(self, obj):
        """Display user as link"""
        url = reverse("admin:users_telegramuser_change", args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>', url, obj.user.telegram_username or obj.user.telegram_id
        )

    @admin.display(description=_("Type"))
    def type_badge(self, obj):
        """Display type as badge"""
        colors = {
            "credit": "green",
            "debit": "red",
            "refund": "blue",
            "bonus": "purple",
            "commission": "orange",
        }
        color = colors.get(obj.type, "gray")
        symbol = "+" if obj.is_credit else "-"

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}{}</span>',
            color,
            symbol,
            obj.get_type_display(),
        )

    @admin.display(description=_("Amount"))
    def amount_display(self, obj):
        """Display amount with color"""
        color = "green" if obj.is_credit else "red"
        symbol = "+" if obj.is_credit else "-"

        return format_html(
            '<span style="color: {}; font-weight: bold;">' "{}{} UZS</span>",
            color,
            symbol,
            obj.amount,
        )

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            "pending": "yellow",
            "processing": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
            "refunded": "purple",
        }
        color = colors.get(obj.status, "gray")

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    actions = ["mark_completed", "mark_failed", "export_to_csv"]

    @admin.action(description=_("Mark as completed"))
    def mark_completed(self, request, queryset):
        """Mark transactions as completed"""
        count = 0
        for transaction in queryset:
            if transaction.status == "pending":
                transaction.complete()
                count += 1

        self.message_user(request, f"{count} transactions marked as completed.")

    @admin.action(description=_("Mark as failed"))
    def mark_failed(self, request, queryset):
        """Mark transactions as failed"""
        count = 0
        for transaction in queryset:
            if transaction.status == "pending":
                transaction.fail("Manually marked as failed by admin")
                count += 1

        self.message_user(request, f"{count} transactions marked as failed.")
