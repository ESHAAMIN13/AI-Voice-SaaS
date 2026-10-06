"""Central exception handler: every API error uses the same JSON format."""

import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Let DRF handle the errors it knows about (401, 403, 404, 405, 400...).
    response = exception_handler(exc, context)

    # Unexpected server error: log the details privately,
    # but never send Python internals to the client.
    if response is None:
        logger.error("Unhandled API error", exc_info=exc)
        return Response(
            {
                "success": False,
                "message": "Something went wrong on our side. Please try again later.",
                "errors": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        message = "Validation failed."
        errors = response.data
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        message = str(detail) if detail else "Request failed."
        errors = None

    response.data = {"success": False, "message": message, "errors": errors}
    return response