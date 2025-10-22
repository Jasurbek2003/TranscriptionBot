from rest_framework import serializers

from .models import TelegramUser


class TelegramUserSerializer(serializers.ModelSerializer):
    """Serializer for Telegram users"""

    full_name = serializers.ReadOnlyField()
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "telegram_id",
            "telegram_username",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "language_code",
            "role",
            "status",
            "is_premium",
            "wallet_balance",
            "total_transcriptions",
            "total_spent",
            "notifications_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "telegram_id",
            "total_transcriptions",
            "total_spent",
            "created_at",
            "updated_at",
        ]

    def get_wallet_balance(self, obj):
        """Get user's wallet balance"""
        try:
            return float(obj.wallet.balance)
        except (AttributeError, ValueError) as e:
            # User has no wallet or invalid balance value
            return 0.0


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user info"""

    class Meta:
        model = TelegramUser
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "language_code",
            "notifications_enabled",
        ]
