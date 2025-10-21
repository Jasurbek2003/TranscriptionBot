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
import sys
import os

from apps.wallet.models import Wallet

# Import payment services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../services/payment'))
from click_service import ClickService
from payme_service import PaymeService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def click_prepare(request):
    """Handle Click payment Prepare request (action=0).

    Official Documentation: https://docs.click.uz/
    This is the first step in Click's two-phase payment process.
    """
    try:
        # Get parameters from request
        if request.method == "POST":
            params = request.POST.dict()
        else:
            params = request.GET.dict()

        logger.info(f"Click Prepare webhook received: {params}")

        # Extract parameters
        click_trans_id = params.get("click_trans_id")
        service_id = params.get("service_id")
        click_paydoc_id = params.get("click_paydoc_id")
        merchant_trans_id = params.get("merchant_trans_id")
        amount = params.get("amount")
        action = params.get("action", "0")
        error = params.get("error")
        error_note = params.get("error_note")
        sign_time = params.get("sign_time")
        sign_string = params.get("sign")

        # Initialize Click service
        from django.conf import settings as django_settings
        click_service = ClickService(
            merchant_id=django_settings.CLICK_MERCHANT_ID,
            service_id=django_settings.CLICK_SERVICE_ID,
            secret_key=django_settings.CLICK_SECRET_KEY,
            test_mode=django_settings.DEBUG
        )

        # Verify signature
        is_valid = click_service.verify_signature(
            click_trans_id=click_trans_id,
            service_id=service_id,
            merchant_trans_id=merchant_trans_id,
            amount=amount,
            action=action,
            sign_time=sign_time,
            sign_string=sign_string
        )

        if not is_valid:
            logger.error(f"Click signature verification failed for transaction {merchant_trans_id}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["SIGN_CHECK_FAILED"],
                    error_note="Invalid signature"
                )
            )

        # Check if Click reported an error
        if error and int(error) < 0:
            logger.warning(f"Click reported error for transaction {merchant_trans_id}: {error} - {error_note}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["ERROR_IN_REQUEST_FROM_CLICK"],
                    error_note=f"Click error: {error_note}"
                )
            )

        # Get transaction
        try:
            trans = Transaction.objects.get(reference_id=merchant_trans_id)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction {merchant_trans_id} not found")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["TRANSACTION_DOES_NOT_EXIST"],
                    error_note="Transaction not found"
                )
            )

        # Verify amount
        if float(amount) != float(trans.amount):
            logger.error(f"Amount mismatch for transaction {merchant_trans_id}: {amount} != {trans.amount}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["INVALID_AMOUNT"],
                    error_note="Incorrect amount"
                )
            )

        # Check if transaction is still pending
        if trans.status != "pending":
            logger.warning(f"Transaction {merchant_trans_id} already processed: {trans.status}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["ALREADY_PAID"],
                    error_note="Transaction already processed"
                )
            )

        # Save Click transaction IDs
        trans.gateway_transaction_id = click_trans_id
        trans.external_id = click_paydoc_id
        trans.gateway = "click"
        trans.save()

        logger.info(f"Click prepare successful for transaction {merchant_trans_id}")

        return JsonResponse(
            click_service.prepare_response(
                click_trans_id=click_trans_id,
                merchant_trans_id=merchant_trans_id,
                merchant_prepare_id=trans.id
            )
        )

    except Exception as e:
        logger.error(f"Click Prepare webhook error: {e}", exc_info=True)
        return JsonResponse({
            "error": -9,
            "error_note": f"Internal error: {str(e)}"
        })


@csrf_exempt
@require_http_methods(["POST", "GET"])
def click_complete(request):
    """Handle Click payment Complete request (action=1).

    Official Documentation: https://docs.click.uz/
    This is the second step in Click's two-phase payment process.
    """
    try:
        # Get parameters from request
        if request.method == "POST":
            params = request.POST.dict()
        else:
            params = request.GET.dict()

        logger.info(f"Click Complete webhook received: {params}")

        # Extract parameters
        click_trans_id = params.get("click_trans_id")
        service_id = params.get("service_id")
        click_paydoc_id = params.get("click_paydoc_id")
        merchant_trans_id = params.get("merchant_trans_id")
        merchant_prepare_id = params.get("merchant_prepare_id")  # ID from prepare step
        amount = params.get("amount")
        action = params.get("action", "1")
        error = params.get("error")
        error_note = params.get("error_note")
        sign_time = params.get("sign_time")
        sign_string = params.get("sign")

        # Initialize Click service
        from django.conf import settings as django_settings
        click_service = ClickService(
            merchant_id=django_settings.CLICK_MERCHANT_ID,
            service_id=django_settings.CLICK_SERVICE_ID,
            secret_key=django_settings.CLICK_SECRET_KEY,
            test_mode=django_settings.DEBUG
        )

        # Verify signature (includes merchant_prepare_id for Complete)
        is_valid = click_service.verify_signature(
            click_trans_id=click_trans_id,
            service_id=service_id,
            merchant_trans_id=merchant_trans_id,
            amount=amount,
            action=action,
            sign_time=sign_time,
            sign_string=sign_string,
            merchant_prepare_id=merchant_prepare_id  # Required for Complete
        )

        if not is_valid:
            logger.error(f"Click signature verification failed for transaction {merchant_trans_id}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["SIGN_CHECK_FAILED"],
                    error_note="Invalid signature"
                )
            )

        # Check if Click reported an error
        if error and int(error) < 0:
            logger.warning(f"Click reported error for transaction {merchant_trans_id}: {error} - {error_note}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["ERROR_IN_REQUEST_FROM_CLICK"],
                    error_note=f"Click error: {error_note}"
                )
            )

        # Get transaction
        try:
            trans = Transaction.objects.get(reference_id=merchant_trans_id)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction {merchant_trans_id} not found")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["TRANSACTION_DOES_NOT_EXIST"],
                    error_note="Transaction not found"
                )
            )

        # Verify amount
        if float(amount) != float(trans.amount):
            logger.error(f"Amount mismatch for transaction {merchant_trans_id}: {amount} != {trans.amount}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["INVALID_AMOUNT"],
                    error_note="Incorrect amount"
                )
            )

        # Check if already completed (idempotency)
        if trans.status == "completed":
            logger.info(f"Transaction {merchant_trans_id} already completed")
            return JsonResponse(
                click_service.complete_response(
                    click_trans_id=click_trans_id,
                    merchant_trans_id=merchant_trans_id,
                    merchant_confirm_id=trans.id
                )
            )

        # Check if transaction was cancelled
        if trans.status == "cancelled":
            logger.warning(f"Cannot complete cancelled transaction {merchant_trans_id}")
            return JsonResponse(
                click_service.error_response(
                    error=click_service.ERROR_CODES["TRANSACTION_CANCELLED"],
                    error_note="Transaction was cancelled"
                )
            )

        # Complete the transaction
        with db_transaction.atomic():
            # Update wallet balance
            wallet = Wallet.objects.select_for_update().get(user=trans.user)
            wallet.balance += trans.amount
            wallet.total_credited += trans.amount
            wallet.last_transaction_at = timezone.now()
            wallet.save()

            # Update transaction status
            trans.status = "completed"
            trans.balance_after = wallet.balance
            trans.processed_at = timezone.now()
            trans.gateway_transaction_id = click_trans_id
            trans.external_id = click_paydoc_id
            trans.gateway = "click"
            trans.save()

        logger.info(f"Click payment completed: {merchant_trans_id}, amount: {amount} UZS")

        return JsonResponse(
            click_service.complete_response(
                click_trans_id=click_trans_id,
                merchant_trans_id=merchant_trans_id,
                merchant_confirm_id=trans.id
            )
        )

    except Exception as e:
        logger.error(f"Click Complete webhook error: {e}", exc_info=True)
        return JsonResponse({
            "error": -9,
            "error_note": f"Internal error: {str(e)}"
        })


@csrf_exempt
@require_http_methods(["POST"])
def payme_webhook(request):
    """Handle Payme payment webhook callbacks (JSON-RPC 2.0).

    Official Documentation: https://developer.help.paycom.uz/

    Payme Merchant API methods:
    - CheckPerformTransaction
    - CreateTransaction
    - PerformTransaction
    - CancelTransaction
    - CheckTransaction
    - GetStatement
    """
    try:
        # Initialize Payme service
        from django.conf import settings as django_settings
        payme_service = PaymeService(
            merchant_id=django_settings.PAYME_MERCHANT_ID,
            secret_key=django_settings.PAYME_SECRET_KEY,
            test_mode=django_settings.DEBUG
        )

        # Verify Basic Auth
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not payme_service.verify_auth(auth_header):
            logger.error("Payme authentication failed")
            return JsonResponse(
                payme_service.error_response(
                    code=payme_service.ERROR_CODES["INSUFFICIENT_PRIVILEGES"],
                    message="Insufficient privileges"
                )
            )

        # Parse JSON-RPC request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Payme request: {e}")
            return JsonResponse(
                payme_service.error_response(
                    code=payme_service.ERROR_CODES["PARSE_ERROR"],
                    message="JSON parsing error"
                )
            )

        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        logger.info(f"Payme webhook: method={method}, params={params}")

        # CheckPerformTransaction
        if method == "CheckPerformTransaction":
            account = params.get("account", {})
            amount = params.get("amount")
            order_id = account.get("order_id")

            if not order_id:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_ACCOUNT"],
                        message="Order ID is required",
                        data="order_id",
                        request_id=request_id
                    )
                )

            try:
                trans = Transaction.objects.get(reference_id=order_id)
            except Transaction.DoesNotExist:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_ACCOUNT"],
                        message="Invalid order_id",
                        data="order_id",
                        request_id=request_id
                    )
                )

            amount_uzs = payme_service.tiyin_to_amount(amount)
            if float(trans.amount) != float(amount_uzs):
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_AMOUNT"],
                        message=f"Amount mismatch",
                        request_id=request_id
                    )
                )

            if trans.status != "pending":
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["CANT_PERFORM_OPERATION"],
                        message=f"Transaction already {trans.status}",
                        request_id=request_id
                    )
                )

            return JsonResponse(
                payme_service.check_perform_transaction_response(
                    allow=True,
                    request_id=request_id
                )
            )

        # CreateTransaction
        elif method == "CreateTransaction":
            payme_trans_id = params.get("id")
            payme_time = params.get("time")
            amount = params.get("amount")
            account = params.get("account", {})
            order_id = account.get("order_id")

            if not order_id:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_ACCOUNT"],
                        message="Order ID is required",
                        data="order_id",
                        request_id=request_id
                    )
                )

            try:
                trans = Transaction.objects.get(reference_id=order_id)
            except Transaction.DoesNotExist:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_ACCOUNT"],
                        message="Invalid order_id",
                        data="order_id",
                        request_id=request_id
                    )
                )

            # Check if already created (idempotency)
            if trans.external_id == payme_trans_id:
                logger.info(f"Payme transaction {payme_trans_id} already created")
                return JsonResponse(
                    payme_service.create_transaction_response(
                        create_time=int(trans.created_at.timestamp() * 1000),
                        transaction=str(trans.id),
                        state=payme_service.STATES["CREATED"],
                        request_id=request_id
                    )
                )

            amount_uzs = payme_service.tiyin_to_amount(amount)
            if float(trans.amount) != float(amount_uzs):
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["INVALID_AMOUNT"],
                        message="Amount mismatch",
                        request_id=request_id
                    )
                )

            if trans.status != "pending":
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["CANT_PERFORM_OPERATION"],
                        message=f"Transaction already {trans.status}",
                        request_id=request_id
                    )
                )

            trans.external_id = payme_trans_id
            trans.gateway = "payme"
            trans.save()

            logger.info(f"Payme transaction created: {payme_trans_id}")

            return JsonResponse(
                payme_service.create_transaction_response(
                    create_time=int(trans.created_at.timestamp() * 1000),
                    transaction=str(trans.id),
                    state=payme_service.STATES["CREATED"],
                    request_id=request_id
                )
            )

        # PerformTransaction
        elif method == "PerformTransaction":
            payme_trans_id = params.get("id")

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id, gateway="payme")
            except Transaction.DoesNotExist:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["TRANSACTION_NOT_FOUND"],
                        message="Transaction not found",
                        request_id=request_id
                    )
                )

            # Check if already completed (idempotency)
            if trans.status == "completed":
                logger.info(f"Payme transaction {payme_trans_id} already completed")
                return JsonResponse(
                    payme_service.perform_transaction_response(
                        transaction=str(trans.id),
                        perform_time=int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                        state=payme_service.STATES["COMPLETED"],
                        request_id=request_id
                    )
                )

            if trans.status in ["cancelled", "failed"]:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["CANT_PERFORM_OPERATION"],
                        message=f"Transaction is {trans.status}",
                        request_id=request_id
                    )
                )

            # Complete the transaction
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

            logger.info(f"Payme payment completed: {trans.reference_id}, amount: {trans.amount} UZS")

            return JsonResponse(
                payme_service.perform_transaction_response(
                    transaction=str(trans.id),
                    perform_time=int(trans.processed_at.timestamp() * 1000),
                    state=payme_service.STATES["COMPLETED"],
                    request_id=request_id
                )
            )

        # CancelTransaction
        elif method == "CancelTransaction":
            payme_trans_id = params.get("id")
            reason = params.get("reason", 5)

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id, gateway="payme")
            except Transaction.DoesNotExist:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["TRANSACTION_NOT_FOUND"],
                        message="Transaction not found",
                        request_id=request_id
                    )
                )

            # Determine cancellation state
            if trans.status == "completed":
                state = payme_service.STATES["CANCELLED_AFTER_COMPLETE"]
                with db_transaction.atomic():
                    wallet = Wallet.objects.select_for_update().get(user=trans.user)
                    wallet.balance -= trans.amount
                    wallet.save()
                    trans.status = "refunded"
                    trans.failed_reason = f"Payme refund: reason {reason}"
                    trans.save()
            else:
                state = payme_service.STATES["CANCELLED"]
                trans.status = "cancelled"
                trans.failed_reason = f"Payme cancellation: reason {reason}"
                trans.save()

            logger.info(f"Payme transaction cancelled: {payme_trans_id}, reason: {reason}")

            return JsonResponse(
                payme_service.cancel_transaction_response(
                    transaction=str(trans.id),
                    cancel_time=payme_service.timestamp_ms(),
                    state=state,
                    request_id=request_id
                )
            )

        # CheckTransaction
        elif method == "CheckTransaction":
            payme_trans_id = params.get("id")

            try:
                trans = Transaction.objects.get(external_id=payme_trans_id, gateway="payme")
            except Transaction.DoesNotExist:
                return JsonResponse(
                    payme_service.error_response(
                        code=payme_service.ERROR_CODES["TRANSACTION_NOT_FOUND"],
                        message="Transaction not found",
                        request_id=request_id
                    )
                )

            state_map = {
                "pending": payme_service.STATES["CREATED"],
                "completed": payme_service.STATES["COMPLETED"],
                "cancelled": payme_service.STATES["CANCELLED"],
                "failed": payme_service.STATES["CANCELLED"],
                "refunded": payme_service.STATES["CANCELLED_AFTER_COMPLETE"],
            }

            return JsonResponse(
                payme_service.check_transaction_response(
                    create_time=int(trans.created_at.timestamp() * 1000),
                    perform_time=int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                    cancel_time=int(trans.updated_at.timestamp() * 1000) if trans.status in ["cancelled", "refunded"] else 0,
                    transaction=str(trans.id),
                    state=state_map.get(trans.status, 0),
                    reason=None,
                    request_id=request_id
                )
            )

        # GetStatement
        elif method == "GetStatement":
            from_time = params.get("from")
            to_time = params.get("to")

            from_dt = timezone.datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
            to_dt = timezone.datetime.fromtimestamp(to_time / 1000, tz=timezone.utc)

            transactions = Transaction.objects.filter(
                gateway="payme",
                created_at__gte=from_dt,
                created_at__lte=to_dt
            ).order_by('created_at')

            state_map = {
                "pending": payme_service.STATES["CREATED"],
                "completed": payme_service.STATES["COMPLETED"],
                "cancelled": payme_service.STATES["CANCELLED"],
                "failed": payme_service.STATES["CANCELLED"],
                "refunded": payme_service.STATES["CANCELLED_AFTER_COMPLETE"],
            }

            trans_list = []
            for trans in transactions:
                if trans.external_id:
                    trans_list.append({
                        "id": trans.external_id,
                        "time": int(trans.created_at.timestamp() * 1000),
                        "amount": payme_service.amount_to_tiyin(trans.amount),
                        "account": {"order_id": trans.reference_id},
                        "create_time": int(trans.created_at.timestamp() * 1000),
                        "perform_time": int(trans.processed_at.timestamp() * 1000) if trans.processed_at else 0,
                        "cancel_time": int(trans.updated_at.timestamp() * 1000) if trans.status in ["cancelled", "refunded"] else 0,
                        "transaction": str(trans.id),
                        "state": state_map.get(trans.status, 0),
                        "reason": None
                    })

            return JsonResponse(
                payme_service.get_statement_response(
                    transactions=trans_list,
                    request_id=request_id
                )
            )

        # Unknown method
        else:
            logger.error(f"Unknown Payme method: {method}")
            return JsonResponse(
                payme_service.error_response(
                    code=payme_service.ERROR_CODES["METHOD_NOT_FOUND"],
                    message=f"Method not found: {method}",
                    request_id=request_id
                )
            )

    except Exception as e:
        logger.error(f"Payme webhook error: {e}", exc_info=True)
        return JsonResponse({
            "error": {
                "code": -32400,
                "message": f"Internal error: {str(e)}"
            },
            "id": data.get("id") if 'data' in locals() else None
        })