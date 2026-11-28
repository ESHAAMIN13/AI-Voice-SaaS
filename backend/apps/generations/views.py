import logging
from math import ceil

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.voices import storage
from config.responses import error_response, success_response

from . import runner
from .files import generation_files
from .history import HistoryItemSerializer
from .models import Generation
from .serializers import (
    GenerationCreateSerializer,
    GenerationDetailSerializer,
    GenerationListSerializer,
    GenerationStatusSerializer,
)
from .tasks import generate_audio

logger = logging.getLogger(__name__)

FINAL_STATUSES = [Generation.Status.COMPLETED, Generation.Status.FAILED]


class GenerationListCreateView(APIView):
    def get_throttles(self):
        # N-6: only creating is limited. The throttle is attached here on purpose,
        # so it works even if no global throttle class is configured.
        if self.request.method == "POST":
            self.throttle_scope = "generate"
            return [ScopedRateThrottle()]
        return []

    def get(self, request):
        # N-5: own generations only, newest first. The History page uses /history/.
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

        generation = serializer.save()  # committed right away (no ATOMIC_REQUESTS)

        # W-9: if the queue (Redis) is down, never leave a job stuck in PENDING
        try:
            generate_audio.delay(str(generation.id))
        except Exception:
            logger.exception("Could not queue generation %s", generation.id)
            runner.mark_failed(
                generation.id,
                runner.QUEUE_FAILURE,
                from_statuses=(Generation.Status.PENDING,),
            )
            return error_response(
                "The voice service is temporarily unavailable. Please try again later.",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return success_response(
            GenerationDetailSerializer(generation).data, status=status.HTTP_201_CREATED
        )


class GenerationHistoryView(APIView):
    """H-1 to H-3: paged history. Page size is fixed by the server."""

    def get(self, request):
        try:
            page = int(request.query_params.get("page", "1"))
            if page < 1:
                raise ValueError
        except ValueError:
            return error_response("Invalid page number.", status=status.HTTP_400_BAD_REQUEST)

        qs = Generation.objects.filter(user=request.user)
        wanted = request.query_params.get("status")
        if wanted:
            if wanted not in Generation.Status.values:
                return error_response(
                    "Invalid status filter.", status=status.HTTP_400_BAD_REQUEST
                )
            qs = qs.filter(status=wanted)
        qs = qs.select_related("audio").order_by("-created_at", "-id")

        size = settings.GENERATION_HISTORY_PAGE_SIZE
        count = qs.count()  # H-7: two queries in total (this one and the page below)
        pages = max(1, ceil(count / size))
        start = (page - 1) * size
        items = list(qs[start : start + size]) if start < count else []
        return success_response(
            {
                "items": HistoryItemSerializer(items, many=True).data,
                "page": page,
                "pages": pages,
                "count": count,
            }
        )


class GenerationDetailView(APIView):
    def get(self, request, pk):
        generation = get_object_or_404(Generation, pk=pk, user=request.user)  # others: 404
        return success_response(GenerationDetailSerializer(generation).data)

    def delete(self, request, pk):
        generation = get_object_or_404(Generation, pk=pk, user=request.user)  # others: 404
        files = generation_files(generation)
        # H-4: the status check and the delete are ONE query, so a job that starts
        # running at this moment cannot be deleted by mistake.
        _, per_model = Generation.objects.filter(
            pk=generation.pk, user=request.user, status__in=FINAL_STATUSES
        ).delete()
        if per_model.get("generations.Generation", 0) == 0:
            return error_response(
                "This generation is still in progress. Please wait until it finishes.",
                status=status.HTTP_409_CONFLICT,
            )
        # H-5: files are removed after the row. A failed delete is only logged (ORPHAN).
        # H-6: usage records stay (their generation link becomes empty).
        if files:
            storage.remove_files(files)
        return success_response({"detail": "Generation deleted."})


class GenerationStatusView(APIView):
    """Small response for the frontend to poll."""

    def get(self, request, pk):
        generation = get_object_or_404(Generation, pk=pk, user=request.user)
        return success_response(GenerationStatusSerializer(generation).data)
