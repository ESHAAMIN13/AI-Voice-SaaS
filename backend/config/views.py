from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .responses import success_response


class HealthCheckView(APIView):
    """Public endpoint to confirm that the API is running."""

    permission_classes = [AllowAny]

    def get(self, request):
        return success_response({"status": "ok", "service": "ai-voice-saas-api"})