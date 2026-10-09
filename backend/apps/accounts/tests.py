from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .models import Profile, User

PASSWORD = "StrongPass#2026x"


class AuthTestBase(APITestCase):
    def setUp(self):
        # Throttle counters live in local memory; reset so tests don't hit 429
        cache.clear()
        self.client = APIClient()

    def make_user(self, email="user@example.com", **extra):
        user = User.objects.create_user(email=email, password=PASSWORD, **extra)
        Profile.objects.create(user=user, full_name="Test User")
        return user

    def login(self, email="user@example.com", password=PASSWORD):
        return self.client.post(
            reverse("auth-login"), {"email": email, "password": password}, format="json"
        )


class RegisterTests(AuthTestBase):
    def test_register_success_creates_user_and_profile(self):
        res = self.client.post(
            reverse("auth-register"),
            {"email": "New@Example.com", "password": PASSWORD, "full_name": "New One"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["success"])
        self.assertEqual(res.json()["data"]["role"], "USER")
        user = User.objects.get(email="new@example.com")  # stored lowercase
        self.assertEqual(user.profile.full_name, "New One")

    def test_register_ignores_role_admin(self):
        res = self.client.post(
            reverse("auth-register"),
            {"email": "evil@example.com", "password": PASSWORD, "role": "ADMIN", "is_staff": True},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        user = User.objects.get(email="evil@example.com")
        self.assertEqual(user.role, "USER")
        self.assertFalse(user.is_staff)

    def test_register_duplicate_email_is_400(self):
        self.make_user()
        res = self.client.post(
            reverse("auth-register"),
            {"email": "USER@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.json()["success"])

    def test_register_weak_password_is_400(self):
        res = self.client.post(
            reverse("auth-register"),
            {"email": "weak@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(User.objects.filter(email="weak@example.com").exists())


class LoginTests(AuthTestBase):
    def test_login_success_returns_tokens(self):
        self.make_user()
        res = self.login()
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["user"]["email"], "user@example.com")

    def test_login_wrong_password_is_401(self):
        self.make_user()
        res = self.login(password="WrongPass")
        self.assertEqual(res.status_code, 401)

    def test_login_unknown_email_is_401_same_as_wrong_password(self):
        res = self.login(email="nobody@example.com")
        self.assertEqual(res.status_code, 401)

    def test_login_inactive_user_is_401(self):
        self.make_user(is_active=False)
        res = self.login()
        self.assertEqual(res.status_code, 401)


class RefreshAndLogoutTests(AuthTestBase):
    def test_refresh_rotates_and_old_token_is_rejected(self):
        self.make_user()
        old = self.login().json()["data"]["refresh"]

        res = self.client.post(reverse("auth-refresh"), {"refresh": old}, format="json")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertIn("access", data)
        self.assertNotEqual(data["refresh"], old)

        reuse = self.client.post(reverse("auth-refresh"), {"refresh": old}, format="json")
        self.assertEqual(reuse.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        self.make_user()
        refresh = self.login().json()["data"]["refresh"]

        res = self.client.post(reverse("auth-logout"), {"refresh": refresh}, format="json")
        self.assertEqual(res.status_code, 200)

        after = self.client.post(reverse("auth-refresh"), {"refresh": refresh}, format="json")
        self.assertEqual(after.status_code, 401)

    def test_logout_without_token_is_400(self):
        res = self.client.post(reverse("auth-logout"), {}, format="json")
        self.assertEqual(res.status_code, 400)


class ProfileTests(AuthTestBase):
    def auth(self):
        access = self.login().json()["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_profile_without_token_is_401(self):
        res = self.client.get(reverse("profile"))
        self.assertEqual(res.status_code, 401)

    def test_profile_returns_own_data(self):
        self.make_user()
        self.make_user(email="other@example.com")
        self.auth()
        res = self.client.get(reverse("profile"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["email"], "user@example.com")

    def test_profile_update_changes_name_but_never_role(self):
        user = self.make_user()
        self.auth()
        res = self.client.put(
            reverse("profile"),
            {"full_name": "Changed", "preferred_language": "ur", "role": "ADMIN"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.role, "USER")
        self.assertEqual(user.profile.full_name, "Changed")
        self.assertEqual(user.profile.preferred_language, "ur")