from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.responses import error_response, success_response

from .models import Generation
from .serializers import (
    GenerationCreateSerializer,
    GenerationDetailSerializer,
    GenerationListSerializer,
    GenerationStatusSerializer,
)


class GenerationListCreateView(APIView):
    def get_throttles(self):
        # N-6: only creating is limited. The throttle is attached here on purpose,
        # so it works even if no global throttle class is configured.
        if self.request.method == "POST":
            self.throttle_scope = "generate"
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        # N-5: own generations only, newest first. Pagination comes in Phase 31.
        qs = Generation.objects.filter(user=request.user)[:100]
        return success_response(GenerationListSerializer(qs, many=True).data)

    def post(self, request):
        serializer = GenerationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # N-6: limit jobs waiting or running at the same time
        active = Generation.objects.filter(
            user=request.user,
            status__in=[Generation.Status.PENDING, Generation.Status.PROCESSING],
        ).count()
        limit = settings.GENERATION_MAX_ACTIVE_PER_USER
        if active >= limit:
            return error_response(
                f"You already have {limit} generations in progress. Please wait for one to finish.",
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        generation = serializer.save()
        return success_response(
            GenerationDetailSerializer(generation).data, status=status.HTTP_201_CREATED
        )


class GenerationDetailView(APIView):
    def get(self, request, pk):
        generation = get_object_or_404(Generation, pk=pk, user=request.user)  # others: 404
        return success_response(GenerationDetailSerializer(generation).data)


class GenerationStatusView(APIView):
    """Small response for the frontend to poll."""

    def get(self, request, pk):
        generation = get_object_or_404(Generation, pk=pk, user=request.user)
        return success_response(GenerationStatusSerializer(generation).data)