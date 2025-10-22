from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Transcription


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    """Admin configuration for transcriptions"""

    list_display = [
        "id",
        "user_link",
        "file_type_badge",
        "duration_display",
        "cost_display",
        "status_badge",
        "rating_display",
        "created_at",
    ]

    list_filter = ["status", "file_type", "quality_level", "language", "rating", "created_at"]

    search_fields = [
        "user__telegram_username",
        "user__telegram_id",
        "transcription_text",
        "file_telegram_id",
    ]

    readonly_fields = [
        "file_telegram_id",
        "word_count_display",
        "processing_time",
        "created_at",
        "updated_at",
        "completed_at",
    ]

    fieldsets = (
        (
            _("User & File"),
            {"fields": ("user", "file_telegram_id", "file_type", "file_size", "duration_seconds")},
        ),
        (
            _("Transcription"),
            {"fields": ("transcription_text", "word_count_display", "language", "quality_level")},
        ),
        (_("Processing"), {"fields": ("status", "processing_time", "error_message", "cost")}),
        (_("Feedback"), {"fields": ("rating", "feedback")}),
        (_("Metadata"), {"fields": ("metadata",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "completed_at")}),
    )

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    @admin.display(description=_("User"))
    def user_link(self, obj):
        """Display user as link"""
        url = reverse("admin:users_telegramuser_change", args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>', url, obj.user.telegram_username or obj.user.telegram_id
        )

    @admin.display(description=_("Type"))
    def file_type_badge(self, obj):
        """Display file type as badge"""
        colors = {"audio": "blue", "video": "purple", "voice": "green", "video_note": "orange"}
        color = colors.get(obj.file_type, "gray")

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_file_type_display(),
        )

    @admin.display(description=_("Duration"))
    def duration_display(self, obj):
        """Display duration in readable format"""
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @admin.display(description=_("Cost"))
    def cost_display(self, obj):
        """Display cost"""
        return format_html('<span style="font-weight: bold;">{:,.2f} UZS</span>', obj.cost)

    @admin.display(description=_("Status"))
    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            "pending": "yellow",
            "processing": "blue",
            "completed": "green",
            "failed": "red",
            "cancelled": "gray",
        }
        color = colors.get(obj.status, "gray")

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_("Rating"))
    def rating_display(self, obj):
        """Display rating as stars"""
        if obj.rating:
            return "⭐" * obj.rating
        return "-"

    @admin.display(description=_("Word Count"))
    def word_count_display(self, obj):
        """Display word count"""
        return f"{obj.word_count:,} words"

    actions = ["mark_completed", "mark_failed", "export_transcriptions"]

    @admin.action(description=_("Mark as completed"))
    def mark_completed(self, request, queryset):
        """Mark transcriptions as completed"""
        count = 0
        for transcription in queryset:
            if transcription.status != "completed":
                transcription.mark_completed()
                count += 1

        self.message_user(request, f"{count} transcriptions marked as completed.")

    @admin.action(description=_("Mark as failed"))
    def mark_failed(self, request, queryset):
        """Mark transcriptions as failed"""
        count = 0
        for transcription in queryset:
            if transcription.status != "failed":
                transcription.mark_failed("Marked as failed by admin")
                count += 1

        self.message_user(request, f"{count} transcriptions marked as failed.")
