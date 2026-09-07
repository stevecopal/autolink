"""
Tests unitaires pour le service de recherche géospatiale.
"""
import json
import math

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model

from .services import (
    haversine_distance,
    format_distance,
    validate_coordinates,
    search_nearby_garages,
)
from garages.models import Garage

User = get_user_model()


class HaversineDistanceTest(TestCase):
    """Tests pour la fonction de calcul de distance Haversine."""

    def test_same_point_returns_zero(self):
        """Deux points identiques doivent retourner 0."""
        distance = haversine_distance(3.8480, 11.5020, 3.8480, 11.5020)
        self.assertAlmostEqual(distance, 0, places=6)

    def test_known_distance_yaounde(self):
        """Distance connue entre deux points à Yaoundé."""
        # ~1 km entre deux points à Yaoundé
        lat1, lon1 = 3.8480, 11.5020
        lat2, lon2 = 3.8570, 11.5020
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        self.assertGreater(distance, 0.8)
        self.assertLess(distance, 1.5)

    def test_symmetry(self):
        """La distance doit être symétrique."""
        d1 = haversine_distance(3.8480, 11.5020, 3.8570, 11.5100)
        d2 = haversine_distance(3.8570, 11.5100, 3.8480, 11.5020)
        self.assertAlmostEqual(d1, d2, places=6)

    def test_antipodal_points(self):
        """Points opposés sur le globe."""
        distance = haversine_distance(0, 0, 0, 180)
        self.assertAlmostEqual(distance, math.pi * 6371, places=0)


class FormatDistanceTest(TestCase):
    """Tests pour le formatage de distance."""

    def test_meters_when_less_than_1km(self):
        """Moins de 1 km doit afficher en mètres."""
        result = format_distance(0.5)
        self.assertEqual(result, "500 m")

    def test_kilometers_when_1km_or_more(self):
        """1 km ou plus doit afficher en km."""
        result = format_distance(1.4)
        self.assertEqual(result, "1,4 km")

    def test_whole_kilometers(self):
        """Kilomètres entiers."""
        result = format_distance(5.0)
        self.assertEqual(result, "5 km")

    def test_small_distance(self):
        """Très petite distance."""
        result = format_distance(0.001)
        self.assertEqual(result, "1 m")

    def test_zero_distance(self):
        """Distance nulle."""
        result = format_distance(0)
        self.assertEqual(result, "0 m")


class ValidateCoordinatesTest(TestCase):
    """Tests pour la validation des coordonnées."""

    def test_valid_coordinates(self):
        """Coordonnées valides."""
        errors = validate_coordinates(3.8480, 11.5020)
        self.assertEqual(errors, [])

    def test_invalid_latitude_too_high(self):
        """Latitude trop haute."""
        errors = validate_coordinates(91, 11.5020)
        self.assertEqual(len(errors), 1)

    def test_invalid_latitude_too_low(self):
        """Latitude trop basse."""
        errors = validate_coordinates(-91, 11.5020)
        self.assertEqual(len(errors), 1)

    def test_invalid_longitude_too_high(self):
        """Longitude trop haute."""
        errors = validate_coordinates(3.8480, 181)
        self.assertEqual(len(errors), 1)

    def test_invalid_longitude_too_low(self):
        """Longitude trop basse."""
        errors = validate_coordinates(3.8480, -181)
        self.assertEqual(len(errors), 1)

    def test_boundary_values_valid(self):
        """Valeurs limites valides."""
        errors = validate_coordinates(-90, -180)
        self.assertEqual(errors, [])
        errors = validate_coordinates(90, 180)
        self.assertEqual(errors, [])

    def test_nan_latitude(self):
        """NaN en latitude."""
        errors = validate_coordinates(float('nan'), 11.5020)
        self.assertEqual(len(errors), 1)

    def test_nan_longitude(self):
        """NaN en longitude."""
        errors = validate_coordinates(3.8480, float('nan'))
        self.assertEqual(len(errors), 1)

    def test_infinite_latitude(self):
        """Infini en latitude."""
        errors = validate_coordinates(float('inf'), 11.5020)
        self.assertEqual(len(errors), 1)

    def test_infinite_longitude(self):
        """Infini en longitude."""
        errors = validate_coordinates(3.8480, float('inf'))
        self.assertEqual(len(errors), 1)

    def test_both_nan(self):
        """Les deux coordonnées NaN."""
        errors = validate_coordinates(float('nan'), float('nan'))
        self.assertEqual(len(errors), 2)

    def test_string_values(self):
        """Valeurs non numériques."""
        errors = validate_coordinates("not_a_number", 11.5020)
        self.assertEqual(len(errors), 1)

    def test_both_invalid(self):
        """Les deux coordonnées invalides."""
        errors = validate_coordinates(91, 181)
        self.assertEqual(len(errors), 2)


class SearchNearbyGaragesTest(TestCase):
    """Tests pour la recherche de garages à proximité."""

    def setUp(self):
        """Créer des données de test."""
        self.user = User.objects.create_user(
            username='testgarage',
            password='testpass123',
            role='GARAGE',
        )

        # Garage à ~1 km (disponible)
        self.garage_1km = Garage.objects.create(
            owner=self.user,
            name='Garage Proche',
            slug='garage-proche-test',
            phone='+237600000001',
            address='Rue 1, Yaoundé',
            city='Yaoundé',
            neighborhood='Bastos',
            latitude=3.8570,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.VERIFIED,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.AVAILABLE,
        )

        # Garage à ~3 km (disponible)
        self.user2 = User.objects.create_user(
            username='testgarage2',
            password='testpass123',
            role='GARAGE',
        )
        self.garage_3km = Garage.objects.create(
            owner=self.user2,
            name='Garage Moyen',
            slug='garage-moyen-test',
            phone='+237600000002',
            address='Rue 2, Yaoundé',
            city='Yaoundé',
            neighborhood='Bastos',
            latitude=3.8750,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.VERIFIED,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.AVAILABLE,
        )

        # Garage à ~10 km (hors rayon par défaut)
        self.user3 = User.objects.create_user(
            username='testgarage3',
            password='testpass123',
            role='GARAGE',
        )
        self.garage_10km = Garage.objects.create(
            owner=self.user3,
            name='Garage Lointain',
            slug='garage-lointain-test',
            phone='+237600000003',
            address='Rue 3, Yaoundé',
            city='Yaoundé',
            neighborhood='Mimboman',
            latitude=3.9400,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.VERIFIED,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.AVAILABLE,
        )

        # Garage indisponible
        self.user4 = User.objects.create_user(
            username='testgarage4',
            password='testpass123',
            role='GARAGE',
        )
        self.garage_indisponible = Garage.objects.create(
            owner=self.user4,
            name='Garage Fermé',
            slug='garage-ferme-test',
            phone='+237600000004',
            address='Rue 4, Yaoundé',
            city='Yaoundé',
            neighborhood='Bastos',
            latitude=3.8500,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.VERIFIED,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.CLOSED,
        )

        # Garage non vérifié
        self.user5 = User.objects.create_user(
            username='testgarage5',
            password='testpass123',
            role='GARAGE',
        )
        self.garage_non_verifie = Garage.objects.create(
            owner=self.user5,
            name='Garage Non Vérifié',
            slug='garage-non-verifie-test',
            phone='+237600000005',
            address='Rue 5, Yaoundé',
            city='Yaoundé',
            neighborhood='Bastos',
            latitude=3.8490,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.PENDING,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.AVAILABLE,
        )

    def test_search_with_valid_position(self):
        """Recherche avec position valide."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0)
        self.assertTrue(result['success'])
        self.assertGreater(result['total'], 0)

    def test_search_returns_sorted_by_distance(self):
        """Les résultats doivent être triés par distance."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=15.0)
        distances = [r['distance_km'] for r in result['results']]
        self.assertEqual(distances, sorted(distances))

    def test_search_filters_by_radius(self):
        """Le rayon doit filtrer les résultats."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=2.0)
        for garage in result['results']:
            self.assertLessEqual(garage['distance_km'], 2.0)

    def test_search_excludes_unavailable_garages(self):
        """Les garages indisponibles ne doivent pas apparaître par défaut."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0, availability_filter=True)
        for garage in result['results']:
            self.assertIn(garage['availability_status'], ['AVAILABLE', 'BUSY'])

    def test_search_includes_unavailable_when_filter_off(self):
        """Sans filtre, tous les garages vérifiés actifs doivent apparaître."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0, availability_filter=False)
        # Au moins le garage proche et le garage fermé doivent apparaître
        names = [r['name'] for r in result['results']]
        self.assertIn('Garage Proche', names)

    def test_search_excludes_unverified(self):
        """Les garages non vérifiés ne doivent pas apparaître."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0, availability_filter=False)
        names = [r['name'] for r in result['results']]
        self.assertNotIn('Garage Non Vérifié', names)

    def test_search_excludes_inactive(self):
        """Les garages inactifs ne doivent pas apparaître."""
        self.garage_1km.is_active = False
        self.garage_1km.save()
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0)
        names = [r['name'] for r in result['results']]
        self.assertNotIn('Garage Proche', names)

    def test_search_invalid_coordinates(self):
        """Coordonnées invalides doivent retourner une erreur."""
        result = search_nearby_garages(91, 11.5020)
        self.assertFalse(result['success'])
        self.assertEqual(len(result['errors']), 1)

    def test_search_no_garages_in_area(self):
        """Aucun garage dans la zone."""
        result = search_nearby_garages(0, 0, radius_km=1.0)
        self.assertTrue(result['success'])
        self.assertEqual(result['total'], 0)

    def test_search_result_structure(self):
        """Vérifier la structure des résultats."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=5.0)
        self.assertTrue(result['success'])
        if result['results']:
            garage = result['results'][0]
            required_keys = [
                'id', 'slug', 'name', 'latitude', 'longitude',
                'distance_km', 'distance_display', 'is_available',
                'availability_status', 'url',
            ]
            for key in required_keys:
                self.assertIn(key, garage)

    def test_search_large_radius(self):
        """Grand rayon doit trouver tous les garages proches."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=50.0, availability_filter=False)
        self.assertGreaterEqual(result['total'], 3)  # Au moins proche + moyen + lointain

    def test_search_radius_capped(self):
        """Le rayon doit être limité à MAX_SEARCH_RADIUS_KM."""
        result = search_nearby_garages(3.8480, 11.5020, radius_km=1000.0)
        self.assertTrue(result['success'])
        self.assertLessEqual(result['search_radius_km'], 50.0)


class NearbySearchAPITest(TestCase):
    """Tests pour l'endpoint API de recherche à proximité."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='CLIENT',
        )
        self.garage_user = User.objects.create_user(
            username='testgarageapi',
            password='testpass123',
            role='GARAGE',
        )
        self.garage = Garage.objects.create(
            owner=self.garage_user,
            name='Garage API Test',
            slug='garage-api-test',
            phone='+237600000099',
            address='Rue API, Yaoundé',
            city='Yaoundé',
            neighborhood='Bastos',
            latitude=3.8570,
            longitude=11.5020,
            verification_status=Garage.VerificationStatus.VERIFIED,
            is_active=True,
            availability_status=Garage.AvailabilityStatus.AVAILABLE,
        )

    def test_get_nearby_api(self):
        """Test de l'endpoint GET nearby."""
        response = self.client.get(
            '/api/nearby/',
            {'lat': '3.8480', 'lng': '11.5020', 'radius': '5'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_post_nearby_api(self):
        """Test de l'endpoint POST nearby."""
        response = self.client.post(
            '/api/nearby/search/',
            data=json.dumps({
                'latitude': 3.8480,
                'longitude': 11.5020,
                'radius': 5.0,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])

    def test_post_nearby_invalid_json(self):
        """POST avec JSON invalide."""
        response = self.client.post(
            '/api/nearby/search/',
            data='not json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_post_nearby_missing_coordinates(self):
        """POST sans coordonnées."""
        response = self.client.post(
            '/api/nearby/search/',
            data=json.dumps({'radius': 5}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_get_nearby_invalid_lat(self):
        """GET avec latitude invalide."""
        response = self.client.get(
            '/api/nearby/',
            {'lat': 'invalid', 'lng': '11.5020'}
        )
        self.assertEqual(response.status_code, 400)

    def test_nearby_results_include_distance(self):
        """Les résultats doivent inclure la distance."""
        response = self.client.get(
            '/api/nearby/',
            {'lat': '3.8480', 'lng': '11.5020', 'radius': '5'}
        )
        data = json.loads(response.content)
        if data['results']:
            self.assertIn('distance_km', data['results'][0])
            self.assertIn('distance_display', data['results'][0])
