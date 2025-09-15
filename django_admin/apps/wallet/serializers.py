from rest_framework import serializers
from .models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for wallet"""

    user_id = serializers.ReadOnlyField(source='user.telegram_id')
    username = serializers.ReadOnlyField(source='user.telegram_username')
    daily_spent = serializers.SerializerMethodField()
    monthly_spent = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            'id',
            'user_id',
            'username',
            'balance',
            'currency',
            'is_active',
            'daily_limit',
            'monthly_limit',
            'daily_spent',
            'monthly_spent',
            'total_credited',
            'total_debited',
            'last_transaction_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'total_credited',
            'total_debited',
            'last_transaction_at',
            'created_at',
            'updated_at'
        ]

    def get_daily_spent(self, obj):
        """Get daily spent amount"""
        return float(obj.get_daily_spent())

    def get_monthly_spent(self, obj):
        """Get monthly spent amount"""
        return float(obj.get_monthly_spent())


class AddBalanceSerializer(serializers.Serializer):
    """Serializer for adding balance"""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False)


class DeductBalanceSerializer(serializers.Serializer):
    """Serializer for deducting balance"""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    description = serializers.CharField(max_length=255, required=False)