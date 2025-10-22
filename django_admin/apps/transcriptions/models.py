from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.enums import MediaType, QualityLevel, TranscriptionStatus


class Transcription(models.Model):
    """Transcription model"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transcriptions",
        verbose_name=_("User"),
    )

    # File information
    file_telegram_id = models.CharField(max_length=255, verbose_name=_("Telegram File ID"))
    file_type = models.CharField(
        max_length=20, choices=[(t.value, t.name) for t in MediaType], verbose_name=_("File Type")
    )
    file_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("File Name"))
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_("File Size (bytes)"))
    duration_seconds = models.IntegerField(verbose_name=_("Duration (seconds)"))

    # Transcription details
    transcription_text = models.TextField(blank=True, verbose_name=_("Transcription Text"))
    language = models.CharField(max_length=10, default="auto", verbose_name=_("Language"))
    quality_level = models.CharField(
        max_length=20,
        choices=[(q.value, q.name) for q in QualityLevel],
        default=QualityLevel.NORMAL.value,
        verbose_name=_("Quality Level"),
    )

    # Processing info
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.name) for s in TranscriptionStatus],
        default=TranscriptionStatus.PENDING.value,
        verbose_name=_("Status"),
    )
    processing_time = models.FloatField(
        null=True, blank=True, verbose_name=_("Processing Time (seconds)")
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))

    # Cost information
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Cost"))

    # Rating
    rating = models.IntegerField(
        null=True, blank=True, choices=[(i, i) for i in range(1, 6)], verbose_name=_("Rating")
    )
    feedback = models.TextField(blank=True, verbose_name=_("Feedback"))

    # Metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))

    class Meta:
        db_table = "transcriptions"
        verbose_name = _("Transcription")
        verbose_name_plural = _("Transcriptions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.file_type} - {self.duration_seconds}s"

    @property
    def duration_minutes(self):
        """Get duration in minutes"""
        return (self.duration_seconds + 59) // 60

    @property
    def word_count(self):
        """Get word count of transcription"""
        if self.transcription_text:
            return len(self.transcription_text.split())
        return 0

    def mark_completed(self):
        """Mark transcription as completed"""
        from django.utils import timezone

        self.status = TranscriptionStatus.COMPLETED.value
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def mark_failed(self, error_message: str):
        """Mark transcription as failed"""
        self.status = TranscriptionStatus.FAILED.value
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])
