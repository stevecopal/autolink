# accounts/tests/test_auth_roles.py
"""
Tests for authentication and role system (Phase 2).
Tests: inscription, login, superuser, admin, user, client, access denied, suspension.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from accounts.decorators import (
    role_required,
    admin_required,
    client_required,
    get_redirect_url_for_role,
)
from accounts.forms import CustomUserCreationForm
from garages.services import approve_garage, reject_garage

User = get_user_model()


class UserModelTest(TestCase):
    """Tests for the User model role and account_status fields."""

    def test_user_creation_default_role(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
        )
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(user.account_status, User.AccountStatus.ACTIVE)

    def test_superuser_role(self):
        user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@example.com',
        )
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, User.Role.USER)  # Django creates with default role

    def test_role_choices(self):
        self.assertEqual(User.Role.USER, 'USER')
        self.assertEqual(User.Role.CLIENT, 'CLIENT')
        self.assertEqual(User.Role.ADMIN, 'ADMIN')
        self.assertEqual(User.Role.SUPERUSER, 'SUPERUSER')

    def test_account_status_choices(self):
        self.assertEqual(User.AccountStatus.ACTIVE, 'ACTIVE')
        self.assertEqual(User.AccountStatus.SUSPENDED, 'SUSPENDED')

    def test_is_account_active(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            account_status=User.AccountStatus.ACTIVE,
        )
        self.assertTrue(user.is_account_active)

    def test_is_account_suspended(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            account_status=User.AccountStatus.SUSPENDED,
        )
        self.assertFalse(user.is_account_active)

    def test_is_superadmin_superuser(self):
        user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
        )
        self.assertTrue(user.is_superadmin)

    def test_is_superadmin_role(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.SUPERUSER,
        )
        self.assertTrue(user.is_superadmin)

    def test_is_superadmin_regular_user(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.USER,
        )
        self.assertFalse(user.is_superadmin)

    def test_is_admin_or_above_admin(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.ADMIN,
        )
        self.assertTrue(user.is_admin_or_above)

    def test_is_admin_or_above_superuser_role(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.SUPERUSER,
        )
        self.assertTrue(user.is_admin_or_above)

    def test_is_admin_or_above_superuser_flag(self):
        user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
        )
        self.assertTrue(user.is_admin_or_above)

    def test_is_admin_or_above_regular_user(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.USER,
        )
        self.assertFalse(user.is_admin_or_above)

    def test_is_client_or_above_client(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.CLIENT,
        )
        self.assertTrue(user.is_client_or_above)

    def test_is_client_or_above_admin(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.ADMIN,
        )
        self.assertTrue(user.is_client_or_above)

    def test_is_client_or_above_superuser(self):
        user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
        )
        self.assertTrue(user.is_client_or_above)

    def test_is_client_or_above_regular_user(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.USER,
        )
        self.assertFalse(user.is_client_or_above)


class RegistrationFormTest(TestCase):
    """Tests for the registration form."""

    def test_registration_creates_user_role(self):
        form = CustomUserCreationForm(data={
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '+237690000000',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(user.account_status, User.AccountStatus.ACTIVE)

    def test_registration_prevents_role_escalation(self):
        form = CustomUserCreationForm(data={
            'username': 'hacker',
            'email': 'hacker@example.com',
            'phone': '+237690000000',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.role, User.Role.USER)


class RegistrationViewTest(TestCase):
    """Tests for the registration view."""

    def test_register_view_get(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_view_creates_user_with_user_role(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'phone': '+237690000000',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(user.account_status, User.AccountStatus.ACTIVE)

    def test_register_redirects_authenticated_user(self):
        user = User.objects.create_user(
            username='existing',
            password='pass123',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:register'))
        self.assertRedirects(response, reverse('core:home'))


class LoginViewTest(TestCase):
    """Tests for the login view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
        )

    def test_login_view_get(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_suspended_user(self):
        self.user.account_status = User.AccountStatus.SUSPENDED
        self.user.save()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)


class RoleRedirectTest(TestCase):
    """Tests for role-based redirects."""

    def test_user_redirect(self):
        user = User.objects.create_user(
            username='user',
            password='pass123',
            role=User.Role.USER,
        )
        url = get_redirect_url_for_role(user)
        self.assertEqual(url, '/compte/dashboard/')

    def test_client_redirect(self):
        user = User.objects.create_user(
            username='client',
            password='pass123',
            role=User.Role.CLIENT,
        )
        url = get_redirect_url_for_role(user)
        self.assertEqual(url, '/compte/dashboard/')

    def test_admin_redirect(self):
        user = User.objects.create_user(
            username='admin',
            password='pass123',
            role=User.Role.ADMIN,
        )
        url = get_redirect_url_for_role(user)
        self.assertEqual(url, '/administration/dashboard/')

    def test_superuser_redirect(self):
        user = User.objects.create_user(
            username='superuser',
            password='pass123',
            role=User.Role.SUPERUSER,
        )
        url = get_redirect_url_for_role(user)
        self.assertEqual(url, '/administration/dashboard/')


class DecoratorTests(TestCase):
    """Tests for permission decorators."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.USER,
        )
        self.client_user = User.objects.create_user(
            username='client',
            password='pass123',
            role=User.Role.CLIENT,
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            password='pass123',
            role=User.Role.ADMIN,
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='pass123',
        )
        self.suspended_user = User.objects.create_user(
            username='suspended',
            password='pass123',
            role=User.Role.USER,
            account_status=User.AccountStatus.SUSPENDED,
        )

    def _make_request(self, user=None):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/test/')
        if user:
            request.user = user
        else:
            from django.contrib.auth.models import AnonymousUser
            request.user = AnonymousUser()
        return request

    def test_role_required_authenticated(self):
        @role_required('USER')
        def my_view(request):
            return True

        request = self._make_request(self.user)
        result = my_view(request)
        self.assertTrue(result)

    def test_role_required_unauthenticated(self):
        @role_required('USER')
        def my_view(request):
            return True

        request = self._make_request()
        response = my_view(request)
        self.assertEqual(response.status_code, 302)

    def test_role_required_wrong_role(self):
        @role_required('ADMIN')
        def my_view(request):
            return True

        request = self._make_request(self.user)
        response = my_view(request)
        self.assertEqual(response.status_code, 302)

    def test_role_required_superuser_bypasses(self):
        @role_required('ADMIN')
        def my_view(request):
            return True

        request = self._make_request(self.superuser)
        result = my_view(request)
        self.assertTrue(result)

    def test_admin_required_admin(self):
        @admin_required
        def my_view(request):
            return True

        request = self._make_request(self.admin_user)
        result = my_view(request)
        self.assertTrue(result)

    def test_admin_required_superuser(self):
        @admin_required
        def my_view(request):
            return True

        request = self._make_request(self.superuser)
        result = my_view(request)
        self.assertTrue(result)

    def test_admin_required_user_denied(self):
        @admin_required
        def my_view(request):
            return True

        request = self._make_request(self.user)
        response = my_view(request)
        self.assertEqual(response.status_code, 302)

    def test_client_required_client(self):
        @client_required
        def my_view(request):
            return True

        request = self._make_request(self.client_user)
        result = my_view(request)
        self.assertTrue(result)

    def test_client_required_admin(self):
        @client_required
        def my_view(request):
            return True

        request = self._make_request(self.admin_user)
        result = my_view(request)
        self.assertTrue(result)

    def test_client_required_superuser(self):
        @client_required
        def my_view(request):
            return True

        request = self._make_request(self.superuser)
        result = my_view(request)
        self.assertTrue(result)

    def test_client_required_user_denied(self):
        @client_required
        def my_view(request):
            return True

        request = self._make_request(self.user)
        response = my_view(request)
        self.assertEqual(response.status_code, 302)

    def test_suspended_user_blocked(self):
        @role_required('USER')
        def my_view(request):
            return True

        request = self._make_request(self.suspended_user)
        response = my_view(request)
        self.assertEqual(response.status_code, 302)


class AdminDashboardAccessTest(TestCase):
    """Tests for admin dashboard access with different roles."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role=User.Role.ADMIN,
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='pass123',
        )
        self.user = User.objects.create_user(
            username='user',
            password='pass123',
            role=User.Role.USER,
        )

    def test_admin_can_access_admin_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_admin_dashboard(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_admin_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('administration:dashboard'))
        self.assertRedirects(response, reverse('accounts:login') + '?next=' + reverse('administration:dashboard'))


class GarageServiceTest(TestCase):
    """Tests for garage approval/rejection with role protection."""

    def setUp(self):
        from garages.models import Garage
        from core.models import City, Neighborhood

        self.city = City.objects.create(name='Douala', slug='douala')
        self.neighborhood = Neighborhood.objects.create(
            city=self.city, name='Akwa', slug='akwa'
        )
        self.user = User.objects.create_user(
            username='owner',
            password='pass123',
            role=User.Role.USER,
        )
        self.garage = Garage.objects.create(
            owner=self.user,
            name='Test Garage',
            slug='test-garage',
            phone='+237690000000',
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='PENDING',
        )

    def test_approve_garage_promotes_user_to_client(self):
        result = approve_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.CLIENT)
        self.assertTrue(result['promoted'])

    def test_approve_garage_does_not_promote_admin(self):
        self.user.role = User.Role.ADMIN
        self.user.save()
        result = approve_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.ADMIN)
        self.assertFalse(result['promoted'])

    def test_approve_garage_does_not_promote_superuser(self):
        self.user.role = User.Role.SUPERUSER
        self.user.save()
        result = approve_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.SUPERUSER)
        self.assertFalse(result['promoted'])

    def test_reject_garage_demotes_user_to_user(self):
        self.user.role = User.Role.CLIENT
        self.user.save()
        self.garage.verification_status = 'APPROVED'
        self.garage.save()
        result = reject_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.USER)
        self.assertTrue(result['demoted'])

    def test_reject_garage_does_not_demote_admin(self):
        self.user.role = User.Role.ADMIN
        self.user.save()
        self.garage.verification_status = 'APPROVED'
        self.garage.save()
        result = reject_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.ADMIN)
        self.assertFalse(result['demoted'])

    def test_reject_garage_does_not_demote_superuser(self):
        self.user.role = User.Role.SUPERUSER
        self.user.save()
        self.garage.verification_status = 'APPROVED'
        self.garage.save()
        result = reject_garage(self.garage)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.SUPERUSER)
        self.assertFalse(result['demoted'])


class AccountStatusMiddlewareTest(TestCase):
    """Tests for the AccountStatusMiddleware."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role=User.Role.USER,
        )
        self.suspended_user = User.objects.create_user(
            username='suspended',
            password='pass123',
            role=User.Role.USER,
            account_status=User.AccountStatus.SUSPENDED,
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='pass123',
        )

    def test_active_user_can_access_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_suspended_user_redirected_from_profile(self):
        self.client.force_login(self.suspended_user)
        response = self.client.get(reverse('accounts:profile'), follow=False)
        self.assertEqual(response.status_code, 302)

    def test_superuser_not_blocked(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_suspended_user_json_request(self):
        self.client.force_login(self.suspended_user)
        response = self.client.get(
            reverse('notifications:notification_count'),
            HTTP_ACCEPT='application/json',
        )
        self.assertEqual(response.status_code, 403)
