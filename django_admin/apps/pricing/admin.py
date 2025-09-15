from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import PricingPlan, Promotion


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    """Admin configuration for pricing plans"""

    list_display = [
        'name',
        'audio_price_display',
        'video_price_display',
        'discount_badge',
        'status_badge',
        'is_default',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'is_default',
        'created_at'
    ]

    search_fields = ['name', 'description']

    fieldsets = (
        (_('Plan Info'), {
            'fields': ('name', 'description', 'is_active', 'is_default')
        }),
        (_('Pricing'), {
            'fields': (
                'audio_price_per_minute',
                'video_price_per_minute',
                'discount_percentage'
            )
        }),
        (_('Quality Multipliers'), {
            'fields': (
                'fast_quality_multiplier',
                'normal_quality_multiplier',
                'high_quality_multiplier'
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


