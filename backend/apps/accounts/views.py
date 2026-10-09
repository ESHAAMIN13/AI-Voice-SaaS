from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from config.responses import success_response

from .models import Profile
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


class PublicAPIView(APIView):
    """Base for endpoints that need no login (register, login, refresh, logout)."""

    permission_classes = [AllowAny]
    authentication_classes = []  # a stale token must not block these endpoints

    def get_authenticate_header(self, request):
        # Without this, DRF turns every 401 into a 403 on views that have
        # no authentication classes.
        return "Bearer"

class RegisterView(PublicAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # a stale token must not block registration
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response = success_response(UserSerializer(user).data)
        response.status_code = status.HTTP_201_CREATED
        return response


class LoginView(PublicAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Wrong credentials are a 401, not a field-level 400
            raise AuthenticationFailed("Invalid email or password.")
        user = serializer.validated_data["user"]
        update_last_login(None, user)

        refresh = RefreshToken.for_user(user)
        return success_response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class RefreshView(PublicAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        # With rotation ON this contains a NEW access and a NEW refresh token
        return success_response(serializer.validated_data)


class LogoutView(PublicAPIView):
    permission_classes = [AllowAny]  # works even if the access token has expired
    authentication_classes = []

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            # Already blacklisted or expired: the user is logged out anyway
            pass
        return success_response({"detail": "Logged out."})


class ProfileView(APIView):
    """GET and PUT /api/profile/ : only the logged-in user's own data."""

    def _get_profile(self, user):
        # Superusers made by createsuperuser have no Profile yet
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile

    def get(self, request):
        self._get_profile(request.user)
        return success_response(UserSerializer(request.user).data)

    def put(self, request):
        profile = self._get_profile(request.user)
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return success_response(UserSerializer(request.user).data)