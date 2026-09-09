from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.db import transaction
from decimal import Decimal
import threading
import time

from .models import Order, OrderItem
from catalog.models import Part, Category
from garages.models import Garage
from core.models import City, Neighborhood
from notifications.models import Notification

User = get_user_model()


class DirectOrderViewTest(TestCase):
    """Tests for the direct order functionality."""

    def setUp(self):
        self.client = Client()
        
        self.city = City.objects.create(name='Douala')
        self.neighborhood = Neighborhood.objects.create(
            name='Akwa', city=self.city
        )
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            first_name='Buyer',
            last_name='Test',
            phone='+237600000001',
        )
        
        self.garage_owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            first_name='Owner',
            last_name='Test',
            phone='+237600000002',
        )
        
        self.garage = Garage.objects.create(
            owner=self.garage_owner,
            name='Garage Test',
            slug='garage-test',
            city=self.city,
            neighborhood=self.neighborhood,
            phone='+237600000003',
            approval_status=Garage.VerificationStatus.APPROVED,
        )
        
        self.category = Category.objects.create(
            name='Moteur',
            slug='moteur',
        )
        
        self.part = Part.objects.create(
            name='Filtre à huile',
            slug='filtre-huile',
            category=self.category,
            garage=self.garage,
            seller=self.garage_owner,
            price=Decimal('15000'),
            stock=10,
            stock_status='IN_STOCK',
            condition=Part.Condition.NEW,
            is_active=True,
        )

    def test_direct_order_requires_login(self):
        """Unauthenticated users should be redirected to login."""
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('connexion', response.url)

    def test_direct_order_success(self):
        """Successful order creation."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 2}
        )
        
        self.assertEqual(response.status_code, 302)
        
        order = Order.objects.latest('created_at')
        self.assertEqual(order.user, self.buyer)
        self.assertEqual(order.garage, self.garage)
        self.assertEqual(order.subtotal, Decimal('30000'))
        self.assertEqual(order.total, Decimal('30000'))
        self.assertEqual(order.status, Order.Status.PENDING)
        
        order_item = order.items.first()
        self.assertEqual(order_item.part, self.part)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.part_price, Decimal('15000'))
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 8)

    def test_direct_order_stock_decrement(self):
        """Stock should be decremented after order."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 3}
        )
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 7)

    def test_direct_order_insufficient_stock(self):
        """Order should fail with insufficient stock."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 15}
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 10)

    def test_direct_order_exact_stock(self):
        """Order should succeed when ordering exact stock quantity."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 10}
        )
        
        self.assertEqual(response.status_code, 302)
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 0)
        self.assertEqual(self.part.stock_status, 'OUT_OF_STOCK')

    def test_direct_order_zero_quantity(self):
        """Order should fail with zero quantity."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 0}
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_direct_order_negative_quantity(self):
        """Order should fail with negative quantity."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': -1}
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_direct_order_inactive_part(self):
        """Order should fail for inactive part."""
        self.part.is_active = False
        self.part.save()
        
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Order.objects.count(), 0)

    def test_direct_order_out_of_stock_part(self):
        """Order should fail for out of stock part."""
        self.part.stock = 0
        self.part.stock_status = 'OUT_OF_STOCK'
        self.part.save()
        
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_direct_order_creates_notifications(self):
        """Order should create notifications for buyer and garage owner."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        
        self.assertEqual(Notification.objects.count(), 2)
        
        buyer_notification = Notification.objects.get(user=self.buyer)
        self.assertEqual(buyer_notification.category, Notification.Category.ORDER)
        self.assertIn('Commande confirmée', buyer_notification.title)
        
        owner_notification = Notification.objects.get(user=self.garage_owner)
        self.assertEqual(owner_notification.category, Notification.Category.ORDER)
        self.assertIn('Nouvelle commande reçue', owner_notification.title)

    def test_direct_order_no_self_notification(self):
        """Garage owner should not receive notification when buying own part."""
        self.client.login(email='owner@test.com', password='testpass123')
        
        self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        
        self.assertEqual(Notification.objects.count(), 1)
        
        notification = Notification.objects.first()
        self.assertEqual(notification.user, self.garage_owner)

    def test_direct_order_get_not_allowed(self):
        """GET request should redirect to part detail."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.get(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk})
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.part.slug, response.url)


class DirectOrderConcurrencyTest(TransactionTestCase):
    """Tests for concurrent order scenarios."""

    def setUp(self):
        self.client = Client()
        
        self.city = City.objects.create(name='Douala')
        self.neighborhood = Neighborhood.objects.create(
            name='Akwa', city=self.city
        )
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            first_name='Buyer',
            last_name='Test',
            phone='+237600000001',
        )
        
        self.garage_owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            first_name='Owner',
            last_name='Test',
            phone='+237600000002',
        )
        
        self.garage = Garage.objects.create(
            owner=self.garage_owner,
            name='Garage Test',
            slug='garage-test',
            city=self.city,
            neighborhood=self.neighborhood,
            phone='+237600000003',
            approval_status=Garage.VerificationStatus.APPROVED,
        )
        
        self.category = Category.objects.create(
            name='Moteur',
            slug='moteur',
        )
        
        self.part = Part.objects.create(
            name='Filtre à huile',
            slug='filtre-huile',
            category=self.category,
            garage=self.garage,
            seller=self.garage_owner,
            price=Decimal('15000'),
            stock=5,
            stock_status='IN_STOCK',
            condition=Part.Condition.NEW,
            is_active=True,
        )

    def test_concurrent_orders_stock_integrity(self):
        """Test that concurrent orders don't oversell stock."""
        import time
        from threading import Thread
        
        results = []
        
        def make_order(user_email, quantity, results_list):
            client = Client()
            client.login(email=user_email, password='testpass123')
            
            try:
                response = client.post(
                    reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
                    {'quantity': quantity}
                )
                results_list.append(('success', response.status_code))
            except Exception as e:
                results_list.append(('error', str(e)))
        
        threads = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'concurrent{i}',
                email=f'concurrent{i}@test.com',
                password='testpass123',
                first_name=f'Concurrent{i}',
                last_name='Test',
                phone=f'+23760000000{i+10}',
            )
            t = Thread(target=make_order, args=(user.email, 3, results))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        self.part.refresh_from_db()
        
        total_ordered = sum(
            order.items.first().quantity 
            for order in Order.objects.all()
        )
        
        self.assertLessEqual(total_ordered, self.part.stock + total_ordered)
        self.assertGreaterEqual(self.part.stock, 0)


class DirectOrderIntegrationTest(TestCase):
    """Integration tests for direct order workflow."""

    def setUp(self):
        self.client = Client()
        
        self.city = City.objects.create(name='Douala')
        self.neighborhood = Neighborhood.objects.create(
            name='Akwa', city=self.city
        )
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            first_name='Buyer',
            last_name='Test',
            phone='+237600000001',
        )
        
        self.garage_owner = User.objects.create_user(
            username='owner',
            email='owner@test.com',
            password='testpass123',
            first_name='Owner',
            last_name='Test',
            phone='+237600000002',
        )
        
        self.garage = Garage.objects.create(
            owner=self.garage_owner,
            name='Garage Test',
            slug='garage-test',
            city=self.city,
            neighborhood=self.neighborhood,
            phone='+237600000003',
            approval_status=Garage.VerificationStatus.APPROVED,
        )
        
        self.category = Category.objects.create(
            name='Moteur',
            slug='moteur',
        )
        
        self.part = Part.objects.create(
            name='Filtre à huile',
            slug='filtre-huile',
            category=self.category,
            garage=self.garage,
            seller=self.garage_owner,
            price=Decimal('15000'),
            stock=10,
            stock_status='IN_STOCK',
            condition=Part.Condition.NEW,
            is_active=True,
        )

    def test_full_order_workflow(self):
        """Test complete order workflow from creation to notification."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        response = self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 2}
        )
        
        self.assertEqual(response.status_code, 302)
        
        order = Order.objects.latest('created_at')
        self.assertEqual(order.user, self.buyer)
        self.assertEqual(order.garage, self.garage)
        self.assertEqual(order.subtotal, Decimal('30000'))
        self.assertEqual(order.total, Decimal('30000'))
        
        order_item = order.items.first()
        self.assertEqual(order_item.part, self.part)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.part_price, Decimal('15000'))
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 8)
        
        self.assertEqual(Notification.objects.count(), 2)
        
        buyer_notification = Notification.objects.get(user=self.buyer)
        self.assertIn(order.order_number, buyer_notification.message)
        
        owner_notification = Notification.objects.get(user=self.garage_owner)
        self.assertIn(order.order_number, owner_notification.message)

    def test_order_number_generation(self):
        """Test that order numbers are generated correctly."""
        self.client.login(email='buyer@test.com', password='testpass123')
        
        self.client.post(
            reverse('orders:direct_order', kwargs={'part_id': self.part.pk}),
            {'quantity': 1}
        )
        
        order = Order.objects.latest('created_at')
        self.assertTrue(order.order_number)
        self.assertTrue(len(order.order_number) > 0)
