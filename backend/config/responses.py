"""Helpers that keep every API response in one predictable format."""

from rest_framework import status as http_status
from rest_framework.response import Response


def success_response(data=None, status=http_status.HTTP_200_OK):
    """Return {"success": true, "data": ...}."""
    return Response({"success": True, "data": data}, status=status)


def error_response(message, errors=None, status=http_status.HTTP_400_BAD_REQUEST):
    """Return {"success": false, "message": ..., "errors": ...}."""
    return Response(
        {"success": False, "message": message, "errors": errors},
        status=status,
    )