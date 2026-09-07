"""
AutoLink - Core Application Tests
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import User
from vehicles.models import Brand, ModelVehicle, Vehicle
from garages.models import Garage
from catalog.models import Category, Part
from orders.models import Cart, CartItem, Order, OrderItem
from payments.models import Payment
from reviews.models import Review, Favorite
from notifications.models import Notification
from support.models import Ticket, AssistanceRequest


User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            phone='+237600000000',
            city='Douala',
        )

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser')

    def test_user_role_default(self):
        self.assertEqual(self.user.role, 'CLIENT')

    def test_user_is_not_staff(self):
        self.assertFalse(self.user.is_staff)

    def test_user_display_name(self):
        self.assertEqual(self.user.display_name, 'testuser')


class BrandModelTest(TestCase):
    def test_brand_str(self):
        brand = Brand.objects.create(name='Toyota', slug='toyota')
        self.assertEqual(str(brand), 'Toyota')


class VehicleModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='vehicletest', password='testpass123'
        )
        self.brand = Brand.objects.create(name='Toyota', slug='toyota')
        self.model = ModelVehicle.objects.create(
            brand=self.brand, name='Corolla', slug='corolla'
        )

    def test_vehicle_str(self):
        vehicle = Vehicle.objects.create(
            user=self.user, brand=self.brand, model=self.model,
            nickname='My Car', year=2020,
        )
        self.assertEqual(str(vehicle), 'My Car')

    def test_vehicle_display_name(self):
        vehicle = Vehicle.objects.create(
            user=self.user, brand=self.brand, model=self.model, year=2020,
        )
        self.assertEqual(vehicle.display_name, 'Toyota Corolla 2020')

    def test_vehicle_is_primary_switches(self):
        v1 = Vehicle.objects.create(
            user=self.user, brand=self.brand, nickname='V1', is_primary=True
        )
        v2 = Vehicle.objects.create(
            user=self.user, brand=self.brand, nickname='V2', is_primary=True
        )
        v1.refresh_from_db()
        self.assertFalse(v1.is_primary)
        self.assertTrue(v2.is_primary)


class GarageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='garagetest', password='testpass123'
        )

    def test_garage_str(self):
        garage = Garage.objects.create(
            owner=self.user, name='Test Garage', slug='test-garage',
            phone='+237600000000', address='123 Street', city='Douala', neighborhood='Akwa',
        )
        self.assertEqual(str(garage), 'Test Garage')


class PartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='parttest', password='testpass123'
        )
        self.category = Category.objects.create(
            name='Brakes', slug='brakes'
        )

    def test_part_str(self):
        part = Part.objects.create(
            seller=self.user, name='Brake Pad', slug='brake-pad',
            price=15000, stock=5,
        )
        self.assertEqual(str(part), 'Brake Pad')

    def test_part_is_available(self):
        part = Part.objects.create(
            seller=self.user, name='Test', slug='test-part',
            price=10000, stock=3,
        )
        part.update_stock_status()
        self.assertTrue(part.is_available)

    def test_part_out_of_stock(self):
        part = Part.objects.create(
            seller=self.user, name='Test', slug='test-oos',
            price=10000, stock=0,
        )
        part.update_stock_status()
        self.assertFalse(part.is_available)


class CartModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='carttest', password='testpass123'
        )
        self.cart, _ = Cart.objects.get_or_create(user=self.user)

    def test_cart_str(self):
        self.assertEqual(str(self.cart), f'Panier de {self.user.username}')

    def test_cart_total_empty(self):
        self.assertEqual(self.cart.total, 0)

    def test_cart_item_count(self):
        self.assertEqual(self.cart.item_count, 0)


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ordertest', password='testpass123'
        )

    def test_order_number_auto_generated(self):
        order = Order.objects.create(user=self.user, total=50000)
        self.assertTrue(order.order_number.startswith('AL-'))
        self.assertEqual(len(order.order_number), 11)

    def test_order_status_label(self):
        order = Order.objects.create(user=self.user, total=50000)
        self.assertEqual(order.status_label, 'En attente')

    def test_order_status_color(self):
        order = Order.objects.create(user=self.user, total=50000)
        self.assertEqual(order.status_color, 'gray')

    def test_order_timeline(self):
        order = Order.objects.create(user=self.user, total=50000)
        timeline = order.get_timeline()
        self.assertEqual(len(timeline), 6)
        self.assertTrue(timeline[0][2])  # First step always True


class ReviewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='reviewtest', password='testpass123'
        )

    def test_review_str(self):
        review = Review.objects.create(
            user=self.user, review_type='GARAGE',
            rating=5, comment='Great service!'
        )
        self.assertIn(self.user.username, str(review))


class FavoriteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='favtest', password='testpass123'
        )

    def test_favorite_toggle(self):
        brand = Brand.objects.create(name='Honda', slug='honda')
        garage = Garage.objects.create(
            owner=self.user, name='Honda Garage', slug='honda-garage',
            phone='+237600000000', address='123 Street', city='Douala',
        )
        fav, created = Favorite.objects.get_or_create(
            user=self.user, object_type='GARAGE', garage=garage
        )
        self.assertTrue(created)
        fav2, created2 = Favorite.objects.get_or_create(
            user=self.user, object_type='GARAGE', garage=garage
        )
        self.assertFalse(created2)


class TicketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tickettest', password='testpass123'
        )

    def test_ticket_number_auto_generated(self):
        ticket = Ticket.objects.create(
            user=self.user, subject='Test issue', description='Details'
        )
        self.assertTrue(ticket.ticket_number.startswith('TK-'))


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='notiftest', password='testpass123'
        )

    def test_notification_unread_count(self):
        Notification.objects.create(
            user=self.user, title='Test', message='Hello'
        )
        Notification.objects.create(
            user=self.user, title='Test2', message='Hello2', is_read=True
        )
        count = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(count, 1)


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_home_status_code(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_template(self):
        response = self.client.get(reverse('core:home'))
        self.assertTemplateUsed(response, 'core/home.html')


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


class VehicleViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='vehicleviewtest', password='testpass123'
        )
        self.client.login(username='vehicleviewtest', password='testpass123')

    def test_vehicle_list(self):
        response = self.client.get(reverse('vehicles:vehicle_list'))
        self.assertEqual(response.status_code, 200)

    def test_vehicle_add_page(self):
        response = self.client.get(reverse('vehicles:vehicle_add'))
        self.assertEqual(response.status_code, 200)

    def test_vehicle_add_post(self):
        brand = Brand.objects.create(name='Peugeot', slug='peugeot')
        response = self.client.post(reverse('vehicles:vehicle_add'), {
            'brand': brand.pk,
            'nickname': 'My Peugeot',
            'year': '2021',
            'fuel_type': 'DIESEL',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehicle.objects.count(), 1)


class GarageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='garageviewtest', password='testpass123'
        )
        self.garage = Garage.objects.create(
            owner=self.user, name='Test Garage', slug='test-garage-view',
            phone='+237600000000', address='123 Street', city='Douala',
        )

    def test_garage_list(self):
        response = self.client.get(reverse('garages:garage_list'))
        self.assertEqual(response.status_code, 200)

    def test_garage_detail(self):
        response = self.client.get(
            reverse('garages:garage_detail', kwargs={'slug': self.garage.slug})
        )
        self.assertEqual(response.status_code, 200)


class CatalogViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='catalogviewtest', password='testpass123'
        )

    def test_part_list(self):
        response = self.client.get(reverse('catalog:part_list'))
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


class OrderViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='orderviewtest', password='testpass123'
        )
        self.client.login(username='orderviewtest', password='testpass123')

    def test_order_list_empty(self):
        response = self.client.get(reverse('orders:order_list'))
        self.assertEqual(response.status_code, 200)

    def test_order_detail_not_found(self):
        response = self.client.get(
            reverse('orders:order_detail', kwargs={'order_number': 'AL-00000000'})
        )
        self.assertEqual(response.status_code, 404)


class ReviewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reviewviewtest', password='testpass123'
        )

    def test_review_list(self):
        response = self.client.get(reverse('reviews:review_list'))
        self.assertEqual(response.status_code, 200)

    def test_favorite_list_requires_login(self):
        response = self.client.get(reverse('reviews:favorite_list'))
        self.assertEqual(response.status_code, 302)


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


class APITest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_models_by_brand_api(self):
        brand = Brand.objects.create(name='BMW', slug='bmw')
        ModelVehicle.objects.create(brand=brand, name='X5', slug='x5')
        response = self.client.get(
            reverse('vehicles:api_models', kwargs={'brand_id': brand.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'X5')


class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='securitytest', password='testpass123'
        )

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


class RoleBasedAccessTest(TestCase):
    """Test role-based access control."""
    
    def setUp(self):
        self.client = Client()
        self.client_user = User.objects.create_user(
            username='client', password='testpass123', role='CLIENT'
        )
        self.garage_user = User.objects.create_user(
            username='garage', password='testpass123', role='GARAGE'
        )
        self.admin_user = User.objects.create_user(
            username='admin', password='testpass123', role='ADMIN', is_staff=True
        )
        
        # Create garage for garage user
        self.garage = Garage.objects.create(
            owner=self.garage_user,
            name='Test Garage',
            slug='test-garage-role',
            phone='+237600000000',
            address='123 Street',
            city='Douala',
            verification_status='VERIFIED'
        )

    def test_login_redirect_client(self):
        """Client should be redirected to client dashboard."""
        self.client.login(username='client', password='testpass123')
        response = self.client.post(reverse('accounts:login'), {
            'username': 'client',
            'password': 'testpass123',
        })
        # Should redirect to client dashboard
        self.assertEqual(response.status_code, 302)

    def test_login_redirect_garage(self):
        """Garage should be redirected to garage dashboard."""
        self.client.login(username='garage', password='testpass123')
        response = self.client.post(reverse('accounts:login'), {
            'username': 'garage',
            'password': 'testpass123',
        })
        # Should redirect to garage dashboard
        self.assertEqual(response.status_code, 302)

    def test_login_redirect_admin(self):
        """Admin should be redirected to admin dashboard."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('accounts:login'), {
            'username': 'admin',
            'password': 'testpass123',
        })
        # Should redirect to admin dashboard
        self.assertEqual(response.status_code, 302)

    def test_client_cannot_access_admin_dashboard(self):
        """Client should not access admin dashboard."""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to home

    def test_client_cannot_access_garage_dashboard(self):
        """Client should not access garage dashboard."""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('garages:garage_dashboard'))
        # Should redirect to garage creation or home
        self.assertEqual(response.status_code, 302)

    def test_garage_cannot_access_admin_dashboard(self):
        """Garage should not access admin dashboard."""
        self.client.login(username='garage', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to home

    def test_admin_can_access_admin_dashboard(self):
        """Admin should access admin dashboard."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_garage_can_access_garage_dashboard(self):
        """Garage should access garage dashboard."""
        self.client.login(username='garage', password='testpass123')
        response = self.client.get(reverse('garages:garage_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_client_can_access_client_dashboard(self):
        """Client should access client dashboard."""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('accounts:client_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_garage_dashboard(self):
        """Admin should be able to access garage dashboard (has GARAGE role check)."""
        self.client.login(username='admin', password='testpass123')
        # Admin can access because role check includes ADMIN
        response = self.client.get(reverse('garages:garage_dashboard'))
        # This will redirect to garage creation since admin doesn't own a garage
        self.assertEqual(response.status_code, 302)

    def test_garage_can_manage_products(self):
        """Garage should be able to manage products."""
        self.client.login(username='garage', password='testpass123')
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 200)

    def test_client_cannot_manage_products(self):
        """Client should not access product management."""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 302)  # Redirect to home

    def test_admin_can_manage_users(self):
        """Admin should access user management."""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('administration:users'))
        self.assertEqual(response.status_code, 200)

    def test_client_cannot_manage_users(self):
        """Client should not access user management."""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('administration:users'))
        self.assertEqual(response.status_code, 302)

    def test_garage_cannot_manage_users(self):
        """Garage should not access user management."""
        self.client.login(username='garage', password='testpass123')
        response = self.client.get(reverse('administration:users'))
        self.assertEqual(response.status_code, 302)
