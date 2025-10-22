from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Wallet
from .serializers import AddBalanceSerializer, DeductBalanceSerializer, WalletSerializer


class WalletViewSet(viewsets.ModelViewSet):
    """ViewSet for wallets"""

    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on permissions"""
        queryset = super().get_queryset()

        # Non-admin users can only see their own wallet
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        return queryset

    @action(detail=False, methods=["get"])
    def my_wallet(self, request):
        """Get current user's wallet"""
        try:
            wallet = Wallet.objects.get(user=request.user)
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response({"error": "Wallet not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def add_balance(self, request, pk=None):
        """Add balance to wallet (admin only)"""
        wallet = self.get_object()
        serializer = AddBalanceSerializer(data=request.data)

        if serializer.is_valid():
            amount = serializer.validated_data["amount"]
            description = serializer.validated_data.get("description", "Admin credit")

            try:
                new_balance = wallet.add_balance(amount, description)
                return Response(
                    {
                        "status": "success",
                        "new_balance": float(new_balance),
                        "message": f"Added {amount} to wallet",
                    }
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def deduct_balance(self, request, pk=None):
        """Deduct balance from wallet (admin only)"""
        wallet = self.get_object()
        serializer = DeductBalanceSerializer(data=request.data)

        if serializer.is_valid():
            amount = serializer.validated_data["amount"]
            description = serializer.validated_data.get("description", "Admin debit")

            try:
                new_balance = wallet.deduct_balance(amount, description)
                return Response(
                    {
                        "status": "success",
                        "new_balance": float(new_balance),
                        "message": f"Deducted {amount} from wallet",
                    }
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def statistics(self, request):
        """Get wallet statistics (admin only)"""
        from django.db.models import Avg, Max, Min, Sum

        stats = Wallet.objects.aggregate(
            total_balance=Sum("balance"),
            average_balance=Avg("balance"),
            max_balance=Max("balance"),
            min_balance=Min("balance"),
            total_credited=Sum("total_credited"),
            total_debited=Sum("total_debited"),
        )

        stats["total_wallets"] = Wallet.objects.count()
        stats["active_wallets"] = Wallet.objects.filter(is_active=True).count()
        stats["inactive_wallets"] = Wallet.objects.filter(is_active=False).count()

        return Response(stats)
