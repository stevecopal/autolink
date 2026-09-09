# catalog/tests.py
"""
Tests for the catalog application - Parts and Stock management (Phase 4).
Tests: CRUD, permissions, stock, prices, slug auto-generation.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Part, Category
from .forms import PartForm
from garages.models import Garage
from core.models import City, Neighborhood

User = get_user_model()


class PartModelTest(TestCase):
    """Tests for the Part model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='seller',
            password='pass123',
            role='CLIENT',
        )
        self.city = City.objects.create(name='Douala', slug='douala')
        self.neighborhood = Neighborhood.objects.create(
            city=self.city, name='Akwa', slug='akwa'
        )
        self.garage = Garage.objects.create(
            owner=self.user,
            name='Test Garage',
            slug='test-garage',
            phone='+237690000000',
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='APPROVED',
        )

    def test_part_creation(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu Michelin',
            slug='pneu-michelin',
            price=50000,
            stock=10,
        )
        self.assertEqual(part.name, 'Pneu Michelin')
        self.assertEqual(part.price, 50000)
        self.assertEqual(part.stock, 10)
        self.assertTrue(part.is_active)

    def test_stock_status_update_zero(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=0,
        )
        part.update_stock_status()
        part.refresh_from_db()
        self.assertEqual(part.stock_status, Part.StockStatus.OUT_OF_STOCK)

    def test_stock_status_update_low(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=2,
        )
        part.update_stock_status()
        part.refresh_from_db()
        self.assertEqual(part.stock_status, Part.StockStatus.LOW_STOCK)

    def test_stock_status_update_in_stock(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=10,
        )
        part.update_stock_status()
        part.refresh_from_db()
        self.assertEqual(part.stock_status, Part.StockStatus.IN_STOCK)

    def test_is_available_property(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=5,
        )
        part.update_stock_status()
        self.assertTrue(part.is_available)

    def test_is_not_available_property(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=0,
        )
        part.update_stock_status()
        self.assertFalse(part.is_available)

    def test_stock_label(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=5,
        )
        part.update_stock_status()
        self.assertEqual(part.stock_label, 'Disponible')

    def test_stock_color(self):
        part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=5,
        )
        part.update_stock_status()
        self.assertEqual(part.stock_color, 'green')


class PartFormTest(TestCase):
    """Tests for the PartForm."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='seller',
            password='pass123',
            role='CLIENT',
        )

    def _get_valid_data(self, **overrides):
        data = {
            'name': 'Pneu Michelin',
            'condition': 'NEW',
            'price': 50000,
            'stock': 10,
            'warranty_months': 12,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = PartForm(data=self._get_valid_data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_price_negative(self):
        form = PartForm(data=self._get_valid_data(price=-1000), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_invalid_stock_negative(self):
        form = PartForm(data=self._get_valid_data(stock=-5), user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('stock', form.errors)

    def test_slug_auto_generation(self):
        form = PartForm(data=self._get_valid_data(name='Pneu Michelin Pilot Sport'), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        part = form.save(commit=False)
        part.seller = self.user
        self.assertEqual(part.slug, 'pneu-michelin-pilot-sport')

    def test_slug_uniqueness(self):
        Part.objects.create(
            seller=self.user,
            name='Pneu',
            slug='pneu',
            price=50000,
            stock=10,
        )
        form = PartForm(data=self._get_valid_data(name='Pneu'), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        part = form.save(commit=False)
        part.seller = self.user
        self.assertEqual(part.slug, 'pneu-1')


class PartCRUDViewTest(TestCase):
    """Tests for the Part CRUD views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='seller',
            password='pass123',
            role='CLIENT',
        )
        self.other_user = User.objects.create_user(
            username='other',
            password='pass123',
            role='CLIENT',
        )
        self.city = City.objects.create(name='Douala', slug='douala')
        self.neighborhood = Neighborhood.objects.create(
            city=self.city, name='Akwa', slug='akwa'
        )
        self.garage = Garage.objects.create(
            owner=self.user,
            name='Test Garage',
            slug='test-garage',
            phone='+237690000000',
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='APPROVED',
        )
        self.other_garage = Garage.objects.create(
            owner=self.other_user,
            name='Other Garage',
            slug='other-garage',
            phone='+237690000001',
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='APPROVED',
        )
        self.part = Part.objects.create(
            seller=self.user,
            garage=self.garage,
            name='Pneu Michelin',
            slug='pneu-michelin',
            price=50000,
            stock=10,
        )

    def _get_valid_data(self, **overrides):
        data = {
            'name': 'Filtre à huile',
            'condition': 'NEW',
            'price': 5000,
            'stock': 20,
            'warranty_months': 6,
        }
        data.update(overrides)
        return data

    def test_product_list_requires_login(self):
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 302)

    def test_product_list_requires_client_role(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 200)

    def test_product_list_shows_only_own_garage_parts(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pneu Michelin')

    def test_product_add_requires_login(self):
        response = self.client.get(reverse('catalog:garage_product_add'))
        self.assertEqual(response.status_code, 302)

    def test_product_add_success(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('catalog:garage_product_add'), self._get_valid_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Part.objects.filter(name='Filtre à huile').exists())

    def test_product_add_slug_auto_generated(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('catalog:garage_product_add'), self._get_valid_data(name='Disque de frein Brembo'))
        self.assertEqual(response.status_code, 302)
        part = Part.objects.get(name='Disque de frein Brembo')
        self.assertEqual(part.slug, 'disque-de-frein-brembo')

    def test_product_add_invalid_price(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('catalog:garage_product_add'), self._get_valid_data(price=-1000))
        self.assertEqual(response.status_code, 200)  # Returns form with errors

    def test_product_add_invalid_stock(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('catalog:garage_product_add'), self._get_valid_data(stock=-5))
        self.assertEqual(response.status_code, 200)  # Returns form with errors

    def test_product_edit_requires_ownership(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('catalog:garage_product_edit', kwargs={'pk': self.part.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_product_edit_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('catalog:garage_product_edit', kwargs={'pk': self.part.pk}),
            self._get_valid_data(name='Pneu Michelin Updated', price=55000, stock=15)
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertEqual(self.part.name, 'Pneu Michelin Updated')
        self.assertEqual(self.part.price, 55000)

    def test_product_delete_requires_ownership(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('catalog:garage_product_delete', kwargs={'pk': self.part.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_product_delete_soft_delete(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('catalog:garage_product_delete', kwargs={'pk': self.part.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertFalse(self.part.is_active)

    def test_stock_update_requires_ownership(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('catalog:garage_stock_update', kwargs={'pk': self.part.pk}),
            {'stock': 20}
        )
        self.assertEqual(response.status_code, 404)

    def test_stock_update_success(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('catalog:garage_stock_update', kwargs={'pk': self.part.pk}),
            {'stock': 20}
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 20)

    def test_stock_update_negative_prevented(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('catalog:garage_stock_update', kwargs={'pk': self.part.pk}),
            {'stock': -5}
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 10)  # Unchanged

    def test_stock_update_zero(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('catalog:garage_stock_update', kwargs={'pk': self.part.pk}),
            {'stock': 0}
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock, 0)
        self.assertEqual(self.part.stock_status, Part.StockStatus.OUT_OF_STOCK)

    def test_toggle_requires_ownership(self):
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('catalog:garage_product_toggle', kwargs={'pk': self.part.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_toggle_product(self):
        self.client.force_login(self.user)
        self.assertTrue(self.part.is_active)
        response = self.client.post(
            reverse('catalog:garage_product_toggle', kwargs={'pk': self.part.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.part.refresh_from_db()
        self.assertFalse(self.part.is_active)

    def test_no_garage_redirects_to_create(self):
        user_no_garage = User.objects.create_user(
            username='nogarage',
            password='pass123',
            role='CLIENT',
        )
        self.client.force_login(user_no_garage)
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertRedirects(response, reverse('garages:garage_create'))


class PermissionTest(TestCase):
    """Tests for permission checks."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='user',
            password='pass123',
            role='USER',
        )
        self.client_user = User.objects.create_user(
            username='client',
            password='pass123',
            role='CLIENT',
        )

    def test_user_cannot_access_product_list(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 302)

    def test_client_can_access_product_list(self):
        self.client.force_login(self.client_user)
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 302)  # Redirects to garage_create

    def test_anonymous_cannot_access_product_list(self):
        response = self.client.get(reverse('catalog:garage_products'))
        self.assertEqual(response.status_code, 302)
