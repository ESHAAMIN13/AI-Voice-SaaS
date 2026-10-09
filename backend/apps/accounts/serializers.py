from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import Profile, User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)  # uses Django's password rules
        return value

    @transaction.atomic
    def create(self, validated_data):
        full_name = validated_data.pop("full_name", "")
        # role is NOT taken from the client; create_user sets USER
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        Profile.objects.create(user=user, full_name=full_name)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Safe user data returned to the frontend. No password."""

    full_name = serializers.CharField(source="profile.full_name", read_only=True)
    preferred_language = serializers.CharField(source="profile.preferred_language", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "role", "full_name", "preferred_language", "created_at"]
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Only these two fields can be edited by the user."""

    class Meta:
        model = Profile
        fields = ["full_name", "preferred_language"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=attrs["password"],
        )
        # Same message for "no such email" and "wrong password",
        # so attackers cannot find out which emails exist.
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()