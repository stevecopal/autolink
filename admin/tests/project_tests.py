"""
Project-level tests for the admin application.

Kept in a single file to avoid long, hard-to-correct test suites.
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminDashboardRedirectTest(TestCase):
    def test_anonymous_user_is_redirected_from_admin_pages(self):
        response = self.client.get(
            reverse("administration:dashboard"), follow=False
        )
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('administration:dashboard')}",
        )

    def test_admin_user_can_access_admin_dashboard(self):
        user = User.objects.create_user(
            username="admin",
            password="test",
            role="ADMIN",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("administration:dashboard"))
        self.assertEqual(response.status_code, 200)
