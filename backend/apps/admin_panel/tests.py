from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Profile, User

PASSWORD = "StrongPass#2026x"


class AdminRoleTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset login throttle counters
        self.client = APIClient()

    def login_as(self, user):
        res = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        access = res.json()["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_ping_without_token_is_401(self):
        res = self.client.get(reverse("admin-ping"))
        self.assertEqual(res.status_code, 401)

    def test_ping_as_user_is_403(self):
        user = User.objects.create_user(email="user@example.com", password=PASSWORD)
        Profile.objects.create(user=user)
        self.login_as(user)
        res = self.client.get(reverse("admin-ping"))
        self.assertEqual(res.status_code, 403)
        self.assertFalse(res.json()["success"])

    def test_ping_as_admin_is_200(self):
        admin = User.objects.create_superuser(email="admin@example.com", password=PASSWORD)
        self.login_as(admin)
        res = self.client.get(reverse("admin-ping"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["role"], "ADMIN")

    def test_superuser_always_gets_admin_role(self):
        admin = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
        self.assertEqual(admin.role, "ADMIN")
        self.assertTrue(admin.is_staff)

    def test_inactive_admin_cannot_login_so_no_access(self):
        admin = User.objects.create_superuser(email="gone@example.com", password=PASSWORD)
        admin.is_active = False
        admin.save()
        res = self.client.post(
            reverse("auth-login"),
            {"email": admin.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

    def test_user_who_registers_with_admin_role_stays_user(self):
        self.client.post(
            reverse("auth-register"),
            {"email": "sneaky@example.com", "password": PASSWORD, "role": "ADMIN"},
            format="json",
        )
        user = User.objects.get(email="sneaky@example.com")
        self.login_as(user)
        res = self.client.get(reverse("admin-ping"))
        self.assertEqual(res.status_code, 403)