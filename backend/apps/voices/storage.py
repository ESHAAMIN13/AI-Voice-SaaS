"""All Supabase Storage access lives in this one file."""

import httpx
from django.conf import settings
import logging
logger = logging.getLogger(__name__)
class StorageError(Exception):
    """Raised when storage fails. The message is safe to log, not to show users."""


def _headers(content_type=None):
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not settings.SUPABASE_URL or not key:
        raise StorageError("Storage is not configured.")
    headers = {"apikey": key}
    # Old-style keys are JWTs and also go in Authorization.
    # New sb_secret_ keys are not JWTs and must only be sent as apikey.
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _base():
    from urllib.parse import urlsplit

    parts = urlsplit(settings.SUPABASE_URL.strip())
    return f"{parts.scheme}://{parts.netloc}"

def _object_url(bucket, path):
    # Keep only scheme + host, even if the .env value has extra path parts
    from urllib.parse import urlsplit

    parts = urlsplit(settings.SUPABASE_URL.strip())
    base = f"{parts.scheme}://{parts.netloc}"
    return f"{base}/storage/v1/object/{bucket}/{path}"


def upload_bytes(bucket, path, data, content_type):
    try:
        res = httpx.post(
            _object_url(bucket, path),
            content=data,
            headers=_headers(content_type),
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise StorageError(f"Upload request failed: {type(exc).__name__}") from exc
    if res.status_code not in (200, 201):
        raise StorageError(f"Upload failed with status {res.status_code}")


def delete_object(bucket, path):
    try:
        res = httpx.delete(_object_url(bucket, path), headers=_headers(), timeout=30)
    except httpx.HTTPError as exc:
        raise StorageError(f"Delete request failed: {type(exc).__name__}") from exc
    if res.status_code == 404:
        return  # already gone
    if res.status_code not in (200, 204):
        raise StorageError(f"Delete failed with status {res.status_code}")


def signed_url(bucket, path, expires_in=60):
    """A temporary link (S-4). The bucket stays private."""
    try:
        res = httpx.post(
            f"{_base()}/storage/v1/object/sign/{bucket}/{path}",
            json={"expiresIn": expires_in},
            headers=_headers(),
            timeout=30,
        )
    except httpx.HTTPError as exc:
        raise StorageError(f"Sign request failed: {type(exc).__name__}") from exc
    if res.status_code != 200:
        raise StorageError(f"Sign failed with status {res.status_code}")
    relative = res.json().get("signedURL")
    if not relative:
        raise StorageError("Sign response had no URL")
    return f"{_base()}/storage/v1{relative}"


def remove_files(items):
    """Delete many files. Never raises (S-3): failures are logged as orphans."""
    for bucket, path in items:
        try:
            delete_object(bucket, path)
        except StorageError:
            logger.error("ORPHAN storage file (delete failed): %s/%s", bucket, path)