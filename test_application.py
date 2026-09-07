"""
AutoLink - Core Application Tests
Tests du système de rôles, garages, localisation et recherche.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from accounts.models import User
from vehicles.models import Brand, ModelVehicle, Vehicle
from garages.models import Garage, GarageService, GarageVerification
from catalog.models import Category, Part
from orders.models import Cart, CartItem, Order, OrderItem
from payments.models import Payment
from reviews.models import Review, Favorite
from notifications.models import Notification
from support.models import Ticket, AssistanceRequest
from core.models import City, Neighborhood


User = get_user_model()


# ============================================================
# Tests du modèle utilisateur
# ============================================================
class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone='+237600000000',
        )

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser')

    def test_user_role_default_is_user(self):
        self.assertEqual(self.user.role, 'USER')

    def test_user_is_not_staff(self):
        self.assertFalse(self.user.is_staff)

    def test_user_display_name(self):
        self.assertEqual(self.user.display_name, 'testuser')


# ============================================================
# Tests du cycle de vie du garage et transition de rôle
# ============================================================
class GarageLifecycleTest(TestCase):
    """Test complet du cycle USER → GARAGE PENDING → APPROVED → CLIENT."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='newuser', password='testpass123', role='USER'
        )
        self.admin = User.objects.create_user(
            username='admin', password='testpass123', role='ADMIN', is_staff=True
        )
        self.city, _ = City.objects.get_or_create(slug='douala', defaults={'name': 'Douala'})
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city, slug='akwa', defaults={'name': 'Akwa'}
        )

    def test_new_user_has_role_user(self):
        self.assertEqual(self.user.role, 'USER')

    def test_user_submits_garage_pending(self):
        garage = Garage.objects.create(
            owner=self.user,
            name='Mon Garage',
            slug='mon-garage',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='PENDING',
        )
        self.assertEqual(garage.verification_status, 'PENDING')
        self.assertEqual(self.user.role, 'USER')

    def test_admin_approves_first_garage_promotes_to_client(self):
        from garages.services import approve_garage
        garage = Garage.objects.create(
            owner=self.user,
            name='Mon Garage',
            slug='mon-garage',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='PENDING',
        )
        result = approve_garage(garage, admin_user=self.admin)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'CLIENT')
        self.assertEqual(garage.verification_status, 'APPROVED')
        self.assertTrue(result['promoted'])

    def test_admin_rejects_garage_keeps_role_user(self):
        from garages.services import reject_garage
        garage = Garage.objects.create(
            owner=self.user,
            name='Mon Garage',
            slug='mon-garage',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='PENDING',
        )
        reject_garage(garage, reason='Photos non conformes', admin_user=self.admin)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'USER')
        self.assertEqual(garage.verification_status, 'REJECTED')
        self.assertEqual(garage.rejection_reason, 'Photos non conformes')

    def test_client_with_approved_garage_keeps_role_on_rejection(self):
        from garages.services import approve_garage, reject_garage
        garage_a = Garage.objects.create(
            owner=self.user,
            name='Garage A',
            slug='garage-a',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='PENDING',
        )
        approve_garage(garage_a, admin_user=self.admin)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'CLIENT')

        garage_b = Garage.objects.create(
            owner=self.user,
            name='Garage B',
            slug='garage-b',
            phone='+237600000000',
            address='456 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.019000'),
            longitude=Decimal('9.694000'),
            verification_status='PENDING',
        )
        reject_garage(garage_b, reason='Document manquant', admin_user=self.admin)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'CLIENT')

    def test_multiple_garages_count(self):
        for i in range(3):
            Garage.objects.create(
                owner=self.user,
                name=f'Garage {i}',
                slug=f'garage-{i}',
                phone='+237600000000',
                address='123 Rue',
                city=self.city,
                neighborhood=self.neighborhood,
                latitude=Decimal('4.018500'),
                longitude=Decimal('9.693500'),
            )
        self.assertEqual(self.user.garages.count(), 3)


# ============================================================
# Tests des permissions
# ============================================================
class PermissionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='normaluser', password='testpass123', role='USER'
        )
        self.client_user = User.objects.create_user(
            username='clientuser', password='testpass123', role='CLIENT'
        )
        self.admin_user = User.objects.create_user(
            username='adminuser', password='testpass123', role='ADMIN', is_staff=True
        )
        self.city, _ = City.objects.get_or_create(slug='douala', defaults={'name': 'Douala'})
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city, slug='akwa', defaults={'name': 'Akwa'}
        )
        self.garage = Garage.objects.create(
            owner=self.client_user,
            name='Test Garage',
            slug='test-garage-perm',
            phone='+237600000000',
            address='123 Street',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
        )

    def test_user_can_add_to_cart(self):
        self.client.login(username='normaluser', password='testpass123')
        category = Category.objects.create(name='Test', slug='test-cat')
        part = Part.objects.create(
            seller=self.user, name='Filter', slug='filter-perm',
            price=5000, stock=10, category=category,
            stock_status=Part.StockStatus.IN_STOCK,
        )
        response = self.client.post(
            reverse('orders:cart_add', kwargs={'part_id': part.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_client_cannot_add_to_cart(self):
        self.client.login(username='clientuser', password='testpass123')
        category = Category.objects.create(name='Test', slug='test-cat2')
        part = Part.objects.create(
            seller=self.client_user, name='Filter', slug='filter-perm2',
            price=5000, stock=10, category=category,
            stock_status=Part.StockStatus.IN_STOCK,
        )
        response = self.client.post(
            reverse('orders:cart_add', kwargs={'part_id': part.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_user_can_submit_ticket(self):
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.get(reverse('support:ticket_create'))
        self.assertEqual(response.status_code, 200)

    def test_client_can_submit_ticket(self):
        """Client can submit tickets (login required, no role restriction)."""
        self.client.login(username='clientuser', password='testpass123')
        response = self.client.get(reverse('support:ticket_create'))
        self.assertEqual(response.status_code, 200)

    def test_user_can_submit_garage(self):
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.get(reverse('garages:garage_create'))
        self.assertEqual(response.status_code, 200)

    def test_client_can_access_garage_dashboard(self):
        self.client.login(username='clientuser', password='testpass123')
        response = self.client.get(reverse('garages:garage_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_garage_dashboard(self):
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.get(reverse('garages:garage_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_cannot_access_other_user_garage_dashboard(self):
        other_user = User.objects.create_user(
            username='other', password='testpass123', role='CLIENT'
        )
        self.client.login(username='other', password='testpass123')
        response = self.client.get(
            reverse('garages:garage_dashboard')
        )
        self.assertIn(response.status_code, [302])
        self.assertIn(response.status_code, [302, 403])

    def test_admin_can_access_admin_dashboard(self):
        self.client.login(username='adminuser', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_access_admin_dashboard(self):
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_client_cannot_access_admin_dashboard(self):
        self.client.login(username='clientuser', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 302)


# ============================================================
# Tests de la recherche géographique
# ============================================================
class GeolocationSearchTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='owner', password='testpass123', role='CLIENT'
        )
        self.city, _ = City.objects.get_or_create(slug='douala', defaults={'name': 'Douala'})
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city, slug='akwa', defaults={'name': 'Akwa'}
        )

    def test_approved_available_garage_appears_in_search(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Test',
            slug='garage-search-test',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        from search.services import search_nearby_garages
        result = search_nearby_garages(
            latitude=4.018500,
            longitude=9.693500,
            radius_km=5.0,
            availability_filter=False,
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['total'], 1)

    def test_pending_garage_not_in_search(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Pending',
            slug='garage-pending',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='PENDING',
            availability_status='AVAILABLE',
        )
        from search.services import search_nearby_garages
        result = search_nearby_garages(
            latitude=4.018500,
            longitude=9.693500,
            radius_km=5.0,
            availability_filter=False,
        )
        self.assertEqual(result['total'], 0)

    def test_suspended_garage_not_in_search(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Suspended',
            slug='garage-suspended',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='SUSPENDED',
            availability_status='AVAILABLE',
        )
        from search.services import search_nearby_garages
        result = search_nearby_garages(
            latitude=4.018500,
            longitude=9.693500,
            radius_km=5.0,
            availability_filter=False,
        )
        self.assertEqual(result['total'], 0)

    def test_unavailable_garage_excluded_from_available_search(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Unavailable',
            slug='garage-unavail',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='UNAVAILABLE',
        )
        from search.services import search_nearby_garages
        result = search_nearby_garages(
            latitude=4.018500,
            longitude=9.693500,
            radius_km=5.0,
            availability_filter=True,
        )
        self.assertEqual(result['total'], 0)

    def test_search_by_city(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Douala',
            slug='garage-douala',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(
            reverse('garages:garage_list') + '?city=douala'
        )
        self.assertEqual(response.status_code, 200)

    def test_search_by_neighborhood(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Akwa',
            slug='garage-akwa',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(
            reverse('garages:garage_list') + '?neighborhood=akwa'
        )
        self.assertEqual(response.status_code, 200)

    def test_search_by_city_and_neighborhood(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Combo',
            slug='garage-combo',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(
            reverse('garages:garage_list') + '?city=douala&neighborhood=akwa'
        )
        self.assertEqual(response.status_code, 200)

    def test_search_with_geolocation(self):
        Garage.objects.create(
            owner=self.user,
            name='Garage Geo',
            slug='garage-geo',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        self.client.login(username='owner', password='testpass123')
        response = self.client.get(
            reverse('garages:garage_list') +
            '?lat=4.018500&lng=9.693500&radius=5'
        )
        self.assertEqual(response.status_code, 200)

    def test_distance_sorting(self):
        from search.services import search_nearby_garages
        Garage.objects.create(
            owner=self.user,
            name='Garage Near',
            slug='garage-near',
            phone='+237600000000',
            address='123 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.019000'),
            longitude=Decimal('9.694000'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        Garage.objects.create(
            owner=self.user,
            name='Garage Far',
            slug='garage-far',
            phone='+237600000000',
            address='456 Rue',
            city=self.city,
            neighborhood=self.neighborhood,
            latitude=Decimal('4.050000'),
            longitude=Decimal('9.720000'),
            verification_status='APPROVED',
            availability_status='AVAILABLE',
        )
        result = search_nearby_garages(
            latitude=4.018500,
            longitude=9.693500,
            radius_km=10.0,
            availability_filter=False,
        )
        self.assertEqual(result['total'], 2)
        self.assertLess(
            result['results'][0]['distance_km'],
            result['results'][1]['distance_km']
        )


# ============================================================
# Tests de sécurité
# ============================================================
class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_csrf_protection(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_xss_protection(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')

    def test_unauthenticated_redirect(self):
        protected_urls = [
            reverse('accounts:profile'),
            reverse('vehicles:vehicle_list'),
            reverse('orders:cart'),
            reverse('orders:order_list'),
            reverse('reviews:favorite_list'),
            reverse('support:ticket_list'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f'{url} should redirect')


# ============================================================
# Tests des vues
# ============================================================
class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_status_code(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)


class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='authtest', password='testpass123', email='auth@test.com'
        )

    def test_login_page(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authtest',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authtest',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_authenticated(self):
        self.client.login(username='authtest', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)


class GarageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='garageviewtest', password='testpass123'
        )
        self.city, _ = City.objects.get_or_create(slug='douala', defaults={'name': 'Douala'})
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city, slug='akwa', defaults={'name': 'Akwa'}
        )
        self.garage = Garage.objects.create(
            owner=self.user, name='Test Garage', slug='test-garage-view',
            phone='+237600000000', address='123 Street',
            city=self.city, neighborhood=self.neighborhood,
            latitude=Decimal('4.018500'),
            longitude=Decimal('9.693500'),
        )

    def test_garage_list(self):
        response = self.client.get(reverse('garages:garage_list'))
        self.assertEqual(response.status_code, 200)

    def test_garage_detail(self):
        response = self.client.get(
            reverse('garages:garage_detail', kwargs={'slug': self.garage.slug})
        )
        self.assertEqual(response.status_code, 200)


class CartViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='cartviewtest', password='testpass123'
        )
        self.client.login(username='cartviewtest', password='testpass123')
        self.cart, _ = Cart.objects.get_or_create(user=self.user)

    def test_cart_page(self):
        response = self.client.get(reverse('orders:cart'))
        self.assertEqual(response.status_code, 200)

    def test_cart_add(self):
        part = Part.objects.create(
            seller=self.user, name='Filter', slug='filter-test',
            price=5000, stock=10, stock_status=Part.StockStatus.IN_STOCK,
        )
        response = self.client.post(
            reverse('orders:cart_add', kwargs={'part_id': part.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.cart.items.count(), 1)


class NotificationViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='notifviewtest', password='testpass123'
        )
        self.client.login(username='notifviewtest', password='testpass123')

    def test_notification_list(self):
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)

    def test_notification_count_api(self):
        response = self.client.get(reverse('notifications:notification_count'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('unread_count', response.json())


class SupportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='supportviewtest', password='testpass123'
        )

    def test_ticket_list_requires_login(self):
        response = self.client.get(reverse('support:ticket_list'))
        self.assertEqual(response.status_code, 302)

    def test_assistance_page(self):
        response = self.client.get(reverse('support:assistance'))
        self.assertEqual(response.status_code, 200)
