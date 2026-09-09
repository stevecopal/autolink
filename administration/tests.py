from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import City, Neighborhood
from administration.models import Announcement

User = get_user_model()


class AdminCRUDPermissionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='pass', role='ADMIN', is_staff=True
        )
        self.city, _ = City.objects.get_or_create(
            slug='test-city-douala',
            defaults={'name': 'Douala Test', 'is_active': True}
        )
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city,
            slug='test-bonamoussadi',
            defaults={'name': 'Bonamoussadi Test', 'is_active': True}
        )

    def test_admin_can_load_cities(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('administration:cities'))
        self.assertEqual(resp.status_code, 200)

    def test_anon_cannot_load_cities(self):
        resp = self.client.get(reverse('administration:cities'))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_can_load_neighborhoods(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('administration:neighborhoods'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_load_announcements(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('administration:announcements'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_load_notifications_admin(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(reverse('administration:notifications_admin'))
        self.assertEqual(resp.status_code, 200)

    def test_city_edit_json_returns_form(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(
            reverse('administration:city_edit', args=[self.city.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('form', data)

    def test_city_edit_invalid_post_returns_errors(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.post(
            reverse('administration:city_edit', args=[self.city.id]),
            {'name': '', 'slug': '', 'is_active': 'on'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertIn(resp.status_code, [200, 400])
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('errors', data)

    def test_city_delete_non_empty_fails(self):
        from garages.models import Garage
        self.client.login(username='admin', password='pass')
        Garage.objects.create(
            name='Test Garage',
            owner=self.admin,
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='APPROVED',
        )
        resp = self.client.post(
            reverse('administration:city_delete', args=[self.city.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('message', data)

    def test_city_delete_empty_succeeds(self):
        self.client.login(username='admin', password='pass')
        city2, _ = City.objects.get_or_create(
            slug='test-city-to-delete',
            defaults={'name': 'To Delete'}
        )
        resp = self.client.post(
            reverse('administration:city_delete', args=[city2.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertTrue(data.get('success'))

    def test_neighborhood_edit_json_returns_form(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(
            reverse('administration:neighborhood_edit', args=[self.neighborhood.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('form', data)

    def test_neighborhood_delete_non_empty_fails(self):
        from garages.models import Garage
        self.client.login(username='admin', password='pass')
        Garage.objects.create(
            name='Test Garage',
            owner=self.admin,
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status='APPROVED',
        )
        resp = self.client.post(
            reverse('administration:neighborhood_delete', args=[self.neighborhood.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('message', data)

    def test_announcement_create_and_edit(self):
        self.client.login(username='admin', password='pass')
        # Create
        resp = self.client.post(
            reverse('administration:announcement_create'),
            {'title': 'Test', 'message': 'Hello', 'status': 'DRAFT'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        ann = Announcement.objects.latest('created_at')
        self.assertEqual(ann.title, 'Test')

        # Edit
        resp = self.client.get(
            reverse('administration:announcement_edit', args=[ann.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('form', data)

    def test_announcement_delete(self):
        self.client.login(username='admin', password='pass')
        ann = Announcement.objects.create(
            title='Delete me', message='bye', created_by=self.admin
        )
        resp = self.client.post(
            reverse('administration:announcement_delete', args=[ann.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertFalse(Announcement.objects.filter(pk=ann.pk).exists())

    def test_announcements_filters_by_search(self):
        self.client.login(username='admin', password='pass')
        Announcement.objects.create(
            title='Important', message='salut tout le monde', created_by=self.admin
        )
        resp = self.client.get(
            reverse('administration:announcements') + '?q=salut'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Important')
