from django.db.models import Avg, Count, Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import Transcription
from .serializers import RateTranscriptionSerializer, TranscriptionSerializer


class TranscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for transcriptions"""

    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset based on permissions"""
        queryset = super().get_queryset()

        # Non-admin users can only see their own transcriptions
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        # Apply filters
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        file_type = self.request.query_params.get("file_type")
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        # Date range filter
        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        return queryset.select_related("user")

    @action(detail=False, methods=["get"])
    def my_transcriptions(self, request):
        """Get current user's transcriptions"""
        transcriptions = self.get_queryset().filter(user=request.user)

        page = self.paginate_queryset(transcriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(transcriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def rate(self, request, pk=None):
        """Rate a transcription"""
        transcription = self.get_object()

        # Check if user owns the transcription
        if transcription.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "You can only rate your own transcriptions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RateTranscriptionSerializer(data=request.data)
        if serializer.is_valid():
            transcription.rating = serializer.validated_data["rating"]
            transcription.feedback = serializer.validated_data.get("feedback", "")
            transcription.save(update_fields=["rating", "feedback", "updated_at"])

            return Response({"status": "success", "message": "Transcription rated successfully"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def statistics(self, request):
        """Get transcription statistics"""
        from datetime import datetime, timedelta

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        stats = Transcription.objects.aggregate(
            total_count=Count("id"),
            total_duration=Sum("duration_seconds"),
            total_cost=Sum("cost"),
            average_duration=Avg("duration_seconds"),
            average_cost=Avg("cost"),
            average_rating=Avg("rating"),
        )

        stats["today_count"] = Transcription.objects.filter(created_at__date=today).count()

        stats["week_count"] = Transcription.objects.filter(created_at__date__gte=week_ago).count()

        stats["month_count"] = Transcription.objects.filter(created_at__date__gte=month_ago).count()

        stats["by_status"] = dict(Transcription.objects.values_list("status").annotate(Count("id")))

        stats["by_file_type"] = dict(
            Transcription.objects.values_list("file_type").annotate(Count("id"))
        )

        return Response(stats)
