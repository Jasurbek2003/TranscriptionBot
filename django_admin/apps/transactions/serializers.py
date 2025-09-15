from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions"""

    user_telegram_id = serializers.ReadOnlyField(source='user.telegram_id')
    user_username = serializers.ReadOnlyField(source='user.telegram_username')
    type_display = serializers.ReadOnlyField(source='get_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = Transaction
        fields = [
            'id',
            'reference_id',
            'user_telegram_id',
            'user_username',
            'type',
            'type_display',
            'amount',
            'balance_before',
            'balance_after',
            'payment_method',
            'status',
            'status_display',
            'description',
            'external_id',
            'processed_at',
            'failed_reason',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'reference_id',
            'balance_before',
            'balance_after',
            'processed_at',
            'created_at',
            'updated_at'
        ]


class CreateTransactionSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions"""

    class Meta:
        model = Transaction
        fields = [
            'user',
            'wallet',
            'type',
            'amount',
            'payment_method',
            'description',
            'external_id'
        ]