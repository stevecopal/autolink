from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import City, Neighborhood
from garages.models import Garage

User = get_user_model()


class Command(BaseCommand):
    help = 'Peuple la base de données avec des données de démonstration'

    def handle(self, *args, **options):
        self.stdout.write('Création des villes et quartiers...')
        cities_data = {
            'Douala': ['Akwa', 'Bonapriso', 'Bonamoussadi', 'Bépanda', 'Deido', 'Logbessou', 'Kotto', 'Essos'],
            'Yaoundé': ['Bastos', 'Mvan', 'Nsam', 'Essomba', 'Nlongkak', 'Mokolo'],
            'Bafoussam': ['Kamkop', 'Djeleng', 'Tyo-Ville', 'Marché A'],
            'Bamenda': ['Commercial Avenue', 'Up Station', 'Mankon', 'Nkwen'],
            'Garoua': ['Yelwa', 'Ketiao', 'Bouba Njida'],
            'Maroua': ['Domayo', 'Fotokol', 'Digigué'],
            'Kumba': ['Mbisin', 'Fiango', 'Kekpane'],
            'Ngaoundéré': ['Plateau', 'WARDS', 'Boudour'],
            'Bertoua': ['Centre', 'Baboua', 'Bélel'],
            'Ebolowa': ['Centre', 'Mvog-Atangana', 'Biyang'],
            'Kribi': ['Centre', 'Lobé', 'Ebodjé'],
            'Limbe': ['Down Beach', 'Batoke', 'Mokundange'],
            'Buéa': ['Molyko', 'Check Point', 'Bokwango'],
        }

        cities = {}
        for city_name, neighborhoods in cities_data.items():
            slug = city_name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
            city, _ = City.objects.get_or_create(slug=slug, defaults={'name': city_name})
            cities[city_name] = city
            for n_name in neighborhoods:
                n_slug = n_name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
                Neighborhood.objects.get_or_create(city=city, slug=n_slug, defaults={'name': n_name})

        self.stdout.write(self.style.SUCCESS(f'{len(cities)} villes créées'))

        self.stdout.write('Création des utilisateurs...')

        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@autolink.cm',
                'first_name': 'Admin',
                'last_name': 'AutoLink',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin.set_password('admin123')
        admin.save()

        client, _ = User.objects.get_or_create(
            username='client',
            defaults={
                'email': 'client@test.com',
                'first_name': 'Jean',
                'last_name': 'Kamga',
                'role': 'CLIENT',
            }
        )
        client.set_password('client123')
        client.save()

        user, _ = User.objects.get_or_create(
            username='user',
            defaults={
                'email': 'user@test.com',
                'first_name': 'Marie',
                'last_name': 'Ngo',
                'role': 'USER',
            }
        )
        user.set_password('user123')
        user.save()

        self.stdout.write(self.style.SUCCESS('3 utilisateurs créés'))

        self.stdout.write('Création des garages...')

        douala = cities['Douala']
        akwa = Neighborhood.objects.get(city=douala, slug='akwa')
        bonapriso = Neighborhood.objects.get(city=douala, slug='bonapriso')

        yaounde = cities['Yaoundé']
        bastos = Neighborhood.objects.get(city=yaounde, slug='bastos')

        garages_data = [
            {
                'owner': client,
                'name': 'Garage AutoPro Douala',
                'slug': 'garage-autopro-douala',
                'description': 'Spécialiste en réparation automobile et carrosserie.',
                'phone': '+237690000001',
                'whatsapp': '+237690000001',
                'email': 'autopro@test.com',
                'address': 'Rue de la Joie, Akwa',
                'city': douala,
                'neighborhood': akwa,
                'latitude': 4.0511,
                'longitude': 9.7679,
                'verification_status': 'APPROVED',
                'availability_status': 'AVAILABLE',
                'is_active': True,
            },
            {
                'owner': client,
                'name': 'Mécanique Générale Bonapriso',
                'slug': 'mecanique-generale-bonapriso',
                'description': 'Entretien et réparation de tous types de véhicules.',
                'phone': '+237690000002',
                'whatsapp': '+237690000002',
                'email': 'mecagen@test.com',
                'address': 'Boulevard de la République, Bonapriso',
                'city': douala,
                'neighborhood': bonapriso,
                'latitude': 4.0185,
                'longitude': 9.6935,
                'verification_status': 'APPROVED',
                'availability_status': 'AVAILABLE',
                'is_active': True,
            },
            {
                'owner': client,
                'name': 'Garage Express Yaoundé',
                'slug': 'garage-express-yaounde',
                'description': 'Réparation rapide et fiable. Pièces d\'origine.',
                'phone': '+237690000003',
                'whatsapp': '+237690000003',
                'email': 'express@test.com',
                'address': 'Avenue Bastos, Bastos',
                'city': yaounde,
                'neighborhood': bastos,
                'latitude': 3.8570,
                'longitude': 11.5020,
                'verification_status': 'APPROVED',
                'availability_status': 'AVAILABLE',
                'is_active': True,
            },
        ]

        for data in garages_data:
            Garage.objects.get_or_create(slug=data['slug'], defaults=data)

        self.stdout.write(self.style.SUCCESS(f'{len(garages_data)} garages créés'))
        self.stdout.write(self.style.SUCCESS('Seed terminé avec succès!'))
        self.stdout.write('')
        self.stdout.write('Comptes de démonstration:')
        self.stdout.write('  Admin:  admin / admin123')
        self.stdout.write('  Client: client / client123')
        self.stdout.write('  User:   user / user123')
