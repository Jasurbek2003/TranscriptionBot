from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Q
from .models import TelegramUser
from .serializers import TelegramUserSerializer, UserUpdateSerializer


class TelegramUserViewSet(viewsets.ModelViewSet):
    """ViewSet for Telegram users"""

    queryset = TelegramUser.objects.all()
    serializer_class = TelegramUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()

        # Non-admin users can only see their own profile
        if not self.request.user.is_staff:
            queryset = queryset.filter(id=self.request.user.id)

        # Apply search filter
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(telegram_username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(telegram_id__icontains=search)
            )

        # Apply status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return TelegramUserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def block(self, request, pk=None):
        """Block a user"""
        user = self.get_object()
        user.block()
        return Response({'status': 'User blocked'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unblock(self, request, pk=None):
        """Unblock a user"""
        user = self.get_object()
        user.unblock()
        return Response({'status': 'User unblocked'})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def statistics(self, request):
        """Get user statistics"""
        from django.db.models import Count, Sum
        from datetime import datetime, timedelta

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        stats = {
            'total_users': TelegramUser.objects.count(),
            'active_users': TelegramUser.objects.filter(status='active').count(),
            'blocked_users': TelegramUser.objects.filter(status='blocked').count(),
            'premium_users': TelegramUser.objects.filter(is_premium=True).count(),
            'new_today': TelegramUser.objects.filter(created_at__date=today).count(),
            'new_this_week': TelegramUser.objects.filter(created_at__date__gte=week_ago).count(),
            'new_this_month': TelegramUser.objects.filter(created_at__date__gte=month_ago).count(),
            'by_language': dict(
                TelegramUser.objects.values_list('language_code').annotate(Count('id'))
            ),
            'by_role': dict(
                TelegramUser.objects.values_list('role').annotate(Count('id'))
            )
        }

        return Response(stats)