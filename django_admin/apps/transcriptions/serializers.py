from rest_framework import serializers
from .models import Transcription


class TranscriptionSerializer(serializers.ModelSerializer):
    """Serializer for transcriptions"""

    user_telegram_id = serializers.ReadOnlyField(source='user.telegram_id')
    user_username = serializers.ReadOnlyField(source='user.telegram_username')
    duration_minutes = serializers.ReadOnlyField()
    word_count = serializers.ReadOnlyField()

    class Meta:
        model = Transcription
        fields = [
            'id',
            'user_telegram_id',
            'user_username',
            'file_telegram_id',
            'file_type',
            'file_size',
            'duration_seconds',
            'duration_minutes',
            'transcription_text',
            'word_count',
            'language',
            'quality_level',
            'status',
            'processing_time',
            'error_message',
            'cost',
            'rating',
            'feedback',
            'created_at',
            'updated_at',
            'completed_at'
        ]
        read_only_fields = [
            'processing_time',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at'
        ]


class RateTranscriptionSerializer(serializers.Serializer):
    """Serializer for rating transcriptions"""

    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(max_length=1000, required=False, allow_blank=True)