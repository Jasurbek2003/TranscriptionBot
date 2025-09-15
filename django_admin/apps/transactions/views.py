from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q, Sum
from .models import Transaction
from .serializers import TransactionSerializer, CreateTransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transactions"""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on permissions"""
        queryset = super().get_queryset()

        # Non-admin users can only see their own transactions
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Apply filters
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(type=type_filter)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Date range filter
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        return queryset.select_related('user', 'wallet')

    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action == 'create':
            return CreateTransactionSerializer
        return TransactionSerializer

    @action(detail=False, methods=['get'])
    def my_transactions(self, request):
        """Get current user's transactions"""
        transactions = self.get_queryset().filter(user=request.user)

        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary"""
        queryset = self.get_queryset()

        summary = {
            'total_transactions': queryset.count(),
            'total_credited': queryset.filter(
                type__in=['credit', 'bonus']
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_debited': queryset.filter(
                type='debit'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending': queryset.filter(status='pending').count(),
            'completed': queryset.filter(status='completed').count(),
            'failed': queryset.filter(status='failed').count(),
        }

        return Response(summary)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        """Mark transaction as completed"""
        transaction = self.get_object()

        if transaction.status != 'pending':
            return Response(
                {'error': 'Transaction is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction.complete()
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def fail(self, request, pk=None):
        """Mark transaction as failed"""
        transaction = self.get_object()
        reason = request.data.get('reason', 'Failed by admin')

        if transaction.status != 'pending':
            return Response(
                {'error': 'Transaction is not pending'},
                status=status.HTTP_400_BAD_REQUEST
            )

        transaction.fail(reason)
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)