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


# ============================================================================
# PAYMENT GATEWAY WEBHOOKS
# ============================================================================

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
import logging
import json
import hashlib
import base64

from apps.wallet.models import Wallet

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def click_webhook(request):
    """Handle Click payment webhook callbacks (prepare and complete)."""
    try:
        # Get parameters from request
        if request.method == "POST":
            params = request.POST.dict()
        else:
            params = request.GET.dict()

        logger.info(f"Click webhook received: {params}")

        # Extract parameters
        click_trans_id = params.get("click_trans_id")
        service_id = params.get("service_id")
        click_paydoc_id = params.get("click_paydoc_id")
        merchant_trans_id = params.get("merchant_trans_id")  # Our transaction reference_id
        amount = params.get("amount")
        action = params.get("action")  # 0 = prepare, 1 = complete
        error = params.get("error")
        error_note = params.get("error_note")
        sign_time = params.get("sign_time")
        sign_string = params.get("sign")

        # Verify signature
        from django.conf import settings as django_settings
        secret_key = django_settings.CLICK_SECRET_KEY

        signature_str = f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{amount}{action}{sign_time}"
        calculated_sign = hashlib.md5(signature_str.encode()).hexdigest()

        if calculated_sign != sign_string:
            logger.error(f"Click signature verification failed")
            return JsonResponse({
                "error": -1,
                "error_note": "Invalid signature"
            })

        # Get transaction
        try:
            trans = Transaction.objects.get(reference_id=merchant_trans_id)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction {merchant_trans_id} not found")
            return JsonResponse({
                "error": -5,
                "error_note": "Transaction not found"
            })

        # Check amount
        if float(amount) != float(trans.amount):
            logger.error(f"Amount mismatch: {amount} != {trans.amount}")
            return JsonResponse({
                "error": -2,
                "error_note": "Incorrect amount"
            })

        # Handle action
        if action == "0":  # Prepare
            if trans.status != "pending":
                return JsonResponse({
                    "error": -4,
                    "error_note": "Transaction already processed"
                })

            # Save Click transaction IDs
            trans.gateway_transaction_id = click_trans_id
            trans.external_id = click_paydoc_id
            trans.save()

            return JsonResponse({
                "error": 0,
                "error_note": "Success",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_prepare_id": trans.id
            })

        elif action == "1":  # Complete
            if trans.status == "completed":
                return JsonResponse({
                    "error": 0,
                    "error_note": "Already completed",
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_confirm_id": trans.id
                })

            # Complete transaction
            with db_transaction.atomic():
                # Update wallet
                wallet = Wallet.objects.select_for_update().get(user=trans.user)
                wallet.balance += trans.amount
                wallet.total_credited += trans.amount
                wallet.last_transaction_at = timezone.now()
                wallet.save()

                # Update transaction
                trans.status = "completed"
                trans.balance_after = wallet.balance
                trans.processed_at = timezone.now()
                trans.gateway_transaction_id = click_trans_id
                trans.external_id = click_paydoc_id
                trans.gateway = "click"
                trans.save()

            logger.info(f"Click payment completed: {merchant_trans_id}, amount: {amount}")

            return JsonResponse({
                "error": 0,
                "error_note": "Success",
                "click_trans_id": click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "merchant_confirm_id": trans.id
            })

        else:
            return JsonResponse({
                "error": -3,
                "error_note": "Unknown action"
            })

    except Exception as e:
        logger.error(f"Click webhook error: {e}", exc_info=True)
        return JsonResponse({
            "error": -9,
            "error_note": f"Internal error: {str(e)}"
        })


@csrf_exempt
@require_http_methods(["POST"])
def payme_webhook(request):
    """Handle Payme payment webhook callbacks (JSON-RPC 2.0)."""
    try:
        # Verify authorization
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        from django.conf import settings as django_settings
        secret_key = django_settings.PAYME_SECRET_KEY

        if not auth_header.startswith("Basic "):
            return JsonResponse({
                "error": {
                    "code": -32504,
                    "message": "Unauthorized"
                }
            })

        encoded_credentials = auth_header.replace("Basic ", "")
        decoded_credentials = base64.b64decode(encoded_credentials).decode()
        expected_credentials = f"Paycom:{secret_key}"

        if decoded_credentials != expected_credentials:
            logger.error("Payme authentication failed")
            return JsonResponse({
                "error": {
                    "code": -32504,
                    "message": "Unauthorized"
                }
            })

        # Parse JSON-RPC request
        data = json.loads(request.body)
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        logger.info(f"Payme webhook: method={method}, params={params}")

        # Handle methods
        if method == "CheckPerformTransaction":
            account = params.get("account", {})
            amount = params.get("amount")  # In tiyin
            order_id = account.get("order_id")

            try:
                trans = Transaction.objects.get(reference_id=order_id)
                amount_uzs = Decimal(amount) / 100

                if trans.amount != amount_uzs:
                    return JsonResponse({
                        "error": {"code": -31001, "message": "Amount mismatch"},
                        "id": request_id
                    })

                if trans.status != "pending":
                    return JsonResponse({
                        "error": {"code": -31008, "message": "Transaction already processed"},
                        "id": request_id
                    })

                return JsonResponse({"result": {"allow": True}, "id": request_id})

            except Transaction.DoesNotExist:
                return JsonResponse({
                    "error": {"code": -31050, "message": "Transaction not found"},
                    "id": request_id
                })

        elif method == "CreateTransaction":
            payme_trans_id = params.get("id")
            account = params.get("account", {})
            order_id = account.get("order_id")

            try:
                trans = Transaction.objects.get(reference_id=order_id)

                if trans.external_id == payme_trans_id:
                    return JsonResponse({
                        "result": {
                            "create_time": int(trans.created_at.timestamp() * 1000),
                            "transaction": str(trans.id),
                            "state": 1
                        },
                        "id": request_id
                    })

                trans.external_id = payme_trans_id
                trans.gateway = "payme"
                trans.save()

                return JsonResponse({
                    "result": {
                        "create_time": int(trans.created_at.timestamp() * 1000),
                        "transaction": str(trans.id),
                        "state": 1
                    },
                    "id": request_id
                })

            except Transaction.DoesNotExist:
                return JsonResponse({
                    "error": {"code": -31050, "message": "Transaction not found"},
                    "id": request_id
                })

        elif method == "PerformTransaction":
            payme_trans_id = params.get("id")

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id)

                if trans.status == "completed":
                    return JsonResponse({
                        "result": {
                            "transaction": str(trans.id),
                            "perform_time": int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                            "state": 2
                        },
                        "id": request_id
                    })

                with db_transaction.atomic():
                    wallet = Wallet.objects.select_for_update().get(user=trans.user)
                    wallet.balance += trans.amount
                    wallet.total_credited += trans.amount
                    wallet.last_transaction_at = timezone.now()
                    wallet.save()

                    trans.status = "completed"
                    trans.balance_after = wallet.balance
                    trans.processed_at = timezone.now()
                    trans.save()

                logger.info(f"Payme payment completed: {trans.reference_id}, amount: {trans.amount}")

                return JsonResponse({
                    "result": {
                        "transaction": str(trans.id),
                        "perform_time": int(trans.processed_at.timestamp() * 1000),
                        "state": 2
                    },
                    "id": request_id
                })

            except Transaction.DoesNotExist:
                return JsonResponse({
                    "error": {"code": -31003, "message": "Transaction not found"},
                    "id": request_id
                })

        elif method == "CancelTransaction":
            payme_trans_id = params.get("id")
            reason = params.get("reason")

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id)

                if trans.status == "cancelled":
                    return JsonResponse({
                        "result": {
                            "transaction": str(trans.id),
                            "cancel_time": int(trans.updated_at.timestamp() * 1000),
                            "state": -1
                        },
                        "id": request_id
                    })

                trans.status = "cancelled"
                trans.failed_reason = f"Payme cancellation: reason {reason}"
                trans.save()

                return JsonResponse({
                    "result": {
                        "transaction": str(trans.id),
                        "cancel_time": int(timezone.now().timestamp() * 1000),
                        "state": -1
                    },
                    "id": request_id
                })

            except Transaction.DoesNotExist:
                return JsonResponse({
                    "error": {"code": -31003, "message": "Transaction not found"},
                    "id": request_id
                })

        elif method == "CheckTransaction":
            payme_trans_id = params.get("id")

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id)

                state_map = {
                    "pending": 1,
                    "completed": 2,
                    "cancelled": -1,
                    "failed": -2
                }

                return JsonResponse({
                    "result": {
                        "create_time": int(trans.created_at.timestamp() * 1000),
                        "perform_time": int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                        "cancel_time": 0,
                        "transaction": str(trans.id),
                        "state": state_map.get(trans.status, 0),
                        "reason": trans.failed_reason if trans.failed_reason else None
                    },
                    "id": request_id
                })

            except Transaction.DoesNotExist:
                return JsonResponse({
                    "error": {"code": -31003, "message": "Transaction not found"},
                    "id": request_id
                })

        elif method == "GetStatement":
            from_time = params.get("from")
            to_time = params.get("to")

            from_dt = timezone.datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
            to_dt = timezone.datetime.fromtimestamp(to_time / 1000, tz=timezone.utc)

            transactions = Transaction.objects.filter(
                gateway="payme",
                created_at__gte=from_dt,
                created_at__lte=to_dt
            )

            trans_list = []
            state_map = {"pending": 1, "completed": 2, "cancelled": -1, "failed": -2}

            for trans in transactions:
                trans_list.append({
                    "id": trans.external_id,
                    "time": int(trans.created_at.timestamp() * 1000),
                    "amount": int(trans.amount * 100),
                    "account": {"order_id": trans.reference_id},
                    "create_time": int(trans.created_at.timestamp() * 1000),
                    "perform_time": int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                    "cancel_time": 0,
                    "transaction": str(trans.id),
                    "state": state_map.get(trans.status, 0),
                    "reason": None
                })

            return JsonResponse({"result": {"transactions": trans_list}, "id": request_id})

        else:
            return JsonResponse({
                "error": {"code": -32601, "message": "Method not found"},
                "id": request_id
            })

    except Exception as e:
        logger.error(f"Payme webhook error: {e}", exc_info=True)
        return JsonResponse({
            "error": {"code": -32400, "message": f"Internal error: {str(e)}"},
            "id": data.get("id") if 'data' in locals() else None
        })