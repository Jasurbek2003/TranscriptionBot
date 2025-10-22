from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import PricingPlan


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    """Admin configuration for pricing plans"""

    list_display = [
        "name",
        "audio_price_display",
        "video_price_display",
        "discount_badge",
        "status_badge",
        "is_default",
        "created_at",
    ]

    list_filter = ["is_active", "is_default", "created_at"]

    search_fields = ["name", "description"]

    fieldsets = (
        (_("Plan Info"), {"fields": ("name", "description", "is_active", "is_default")}),
        (
            _("Pricing"),
            {"fields": ("audio_price_per_minute", "video_price_per_minute", "discount_percentage")},
        ),
        (
            _("Quality Multipliers"),
            {
                "fields": (
                    "fast_quality_multiplier",
                    "normal_quality_multiplier",
                    "high_quality_multiplier",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Limits"),
            {"fields": ("max_duration_seconds", "max_file_size_mb"), "classes": ("collapse",)},
        ),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-is_default", "-is_active", "-created_at"]

    @admin.display(
        description=_("Audio Price"),
        ordering="audio_price_per_minute",
    )
    def audio_price_display(self, obj):
        """Display audio price with formatting"""
        return format_html("<strong>{}</strong> sum/min", obj.audio_price_per_minute)

    @admin.display(
        description=_("Video Price"),
        ordering="video_price_per_minute",
    )
    def video_price_display(self, obj):
        """Display video price with formatting"""
        return format_html("<strong>{}</strong> sum/min", obj.video_price_per_minute)

    @admin.display(description=_("Discount"))
    def discount_badge(self, obj):
        """Display discount badge"""
        if obj.discount_percentage > 0:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">-{:.0f}%</span>',
                obj.discount_percentage,
            )
        return format_html('<span style="color: #999;">No discount</span>')

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        """Display status badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">ACTIVE</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">INACTIVE</span>'
        )
