from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AdminCRUDPermissionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin', password='pass', role='ADMIN', is_staff=True
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
            reverse('administration:city_edit', args=[1]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('form', data)

    def test_city_edit_invalid_post_returns_errors(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.post(
            reverse('administration:city_edit', args=[1]),
            {'name': '', 'slug': '', 'is_active': 'on'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('errors', data)

    def test_city_delete_non_empty_fails(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.post(
            reverse('administration:city_delete', args=[1]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('message', data)

    def test_neighborhood_edit_json_returns_form(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(
            reverse('administration:neighborhood_edit', args=[1]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('form', data)

    def test_neighborhood_delete_non_empty_fails(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.post(
            reverse('administration:neighborhood_delete', args=[1]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('message', data)

    def test_announcement_edit_missing_returns_404(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(
            reverse('administration:announcement_edit', args=[99999]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 404)

    def test_announcements_filters_by_search(self):
        self.client.login(username='admin', password='pass')
        resp = self.client.get(
            reverse('administration:announcements') + '?q=salut'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '?q=salut')
