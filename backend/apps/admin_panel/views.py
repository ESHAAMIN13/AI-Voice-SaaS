from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole
from config.responses import success_response


class AdminPingView(APIView):
    """Temporary endpoint to prove that admin-only protection works."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return success_response({"status": "ok", "role": request.user.role})