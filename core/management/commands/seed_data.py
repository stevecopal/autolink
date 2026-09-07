from django.core.management.base import BaseCommand
from django.utils.text import slugify
from accounts.models import User
from vehicles.models import Brand, ModelVehicle, Vehicle
from garages.models import Garage, GarageService
from catalog.models import Category, Part, Compatibility
from core.models import City, Neighborhood


class Command(BaseCommand):
    help = 'Peuple la base avec des données de démonstration'

    def handle(self, *args, **options):
        self.stdout.write('Création des données de démonstration...')

        cities_data = {
            'Douala': ['Akwa', 'Bonapriso', 'Bonamoussadi', 'Bépanda', 'Deido', 'Logbessou', 'Kotto', 'Essos'],
            'Yaoundé': ['Bastos', 'Mvan', 'Nsam', 'Essomba', 'Bastos', 'Nlongkak', 'Mokolo'],
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
            city, _ = City.objects.get_or_create(
                slug=slugify(city_name),
                defaults={'name': city_name}
            )
            cities[city_name] = city
            for n_name in neighborhoods:
                Neighborhood.objects.get_or_create(
                    city=city,
                    slug=slugify(n_name),
                    defaults={'name': n_name}
                )

        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@autolink.cm',
                'first_name': 'Admin',
                'last_name': 'AutoLink',
                'is_staff': True,
                'is_superuser': True,
                'role': 'ADMIN',
                'city': 'Douala',
            }
        )
        admin.set_password('admin123')
        admin.save()

        client, _ = User.objects.get_or_create(
            username='client1',
            defaults={
                'email': 'client@example.com',
                'first_name': 'Jean',
                'last_name': 'Kamga',
                'phone': '+237690000001',
                'city': 'Douala',
                'neighborhood': 'Bonamoussadi',
                'role': 'CLIENT',
            }
        )
        client.set_password('client123')
        client.save()

        user, _ = User.objects.get_or_create(
            username='user1',
            defaults={
                'email': 'user@example.com',
                'first_name': 'Marie',
                'last_name': 'Ngo',
                'phone': '+237690000003',
                'role': 'USER',
            }
        )
        user.set_password('user123')
        user.save()

        brands_data = ['Toyota', 'Hyundai', 'Honda', 'Mercedes-Benz', 'BMW', 'Renault', 'Peugeot', 'Ford', 'Nissan', 'Kia', 'Bosch', 'NGK', 'Gates', 'KYB', 'Denso']
        brands = {}
        for name in brands_data:
            brand, _ = Brand.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name}
            )
            brands[name] = brand

        models_data = [
            ('Toyota', 'Corolla', 2015, 2023),
            ('Toyota', 'Yaris', 2010, 2023),
            ('Toyota', 'RAV4', 2013, 2023),
            ('Hyundai', 'Tucson', 2015, 2023),
            ('Hyundai', 'i10', 2010, 2023),
            ('Honda', 'Civic', 2012, 2023),
            ('Honda', 'CR-V', 2012, 2023),
            ('Renault', 'Clio', 2010, 2023),
            ('Peugeot', '208', 2012, 2023),
            ('Ford', 'Ranger', 2012, 2023),
        ]
        vehicle_models = {}
        for brand_name, model_name, ystart, yend in models_data:
            mv, _ = ModelVehicle.objects.get_or_create(
                brand=brands[brand_name],
                slug=slugify(model_name),
                defaults={'name': model_name, 'year_start': ystart, 'year_end': yend}
            )
            vehicle_models[(brand_name, model_name)] = mv

        Vehicle.objects.get_or_create(
            user=client,
            brand=brands['Toyota'],
            model=vehicle_models[('Toyota', 'Corolla')],
            defaults={
                'nickname': 'Ma Corolla',
                'year': 2018,
                'engine': '1.8',
                'fuel_type': 'ESSENCE',
                'transmission': 'AUTOMATIC',
                'is_primary': True,
            }
        )

        categories_data = [
            ('Freinage', 'brakes', '🔧'),
            ('Moteur', 'engine', '⚙️'),
            ('Électrique', 'electrical', '⚡'),
            ('Suspension', 'suspension', '🔩'),
            ('Climatisation', 'ac', '❄️'),
            ('Pneumatique', 'tires', '🛞'),
            ('Vidange', 'oil', '🛢️'),
            ('Échappement', 'exhaust', '💨'),
        ]
        categories = {}
        for name, slug, icon in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon}
            )
            categories[slug] = cat

        douala = cities.get('Douala')
        bonapriso = Neighborhood.objects.filter(city=douala, slug='bonapriso').first()

        garage, _ = Garage.objects.get_or_create(
            slug=slugify('garage-autoplus'),
            defaults={
                'owner': client,
                'name': 'Garage AutoPlus',
                'description': 'Spécialiste Toyota et Hyundai. Diagnostic professionnel, entretien et réparation.',
                'phone': '+237690000010',
                'whatsapp': '237690000010',
                'address': 'Rue Joss, Bonapriso',
                'city': douala,
                'neighborhood': bonapriso,
                'latitude': 4.0185,
                'longitude': 9.6935,
                'verification_status': 'APPROVED',
                'opening_time': '08:00',
                'closing_time': '18:00',
                'open_weekends': False,
                'trust_score': 4.7,
                'total_reviews': 42,
                'total_orders': 156,
                'is_active': True,
            }
        )

        services_data = [
            ('Diagnostic électronique', 'DIAGNOSTIC', 'Analyse complète du véhicule', 5000, 15000, 60),
            ('Vidange moteur', 'OIL_CHANGE', 'Vidange huile + filtre', 10000, 25000, 45),
            ('Réparation freins', 'BRAKES', 'Plaquettes, disques, liquide', 15000, 80000, 120),
            ('Entretien climatisation', 'AIR_CONDITIONING', 'Recharge, diagnostic, réparation', 10000, 50000, 90),
            ('Pneumatique', 'TIRE', 'Montage, équilibrage, parallélisme', 5000, 30000, 30),
        ]
        for name, cat, desc, pmin, pmax, dur in services_data:
            GarageService.objects.get_or_create(
                garage=garage,
                name=name,
                defaults={
                    'category': cat,
                    'description': desc,
                    'price_min': pmin,
                    'price_max': pmax,
                    'duration_minutes': dur,
                }
            )

        parts_data = [
            ('Plaquettes de frein avant', 'brakes', 'Bosch', 12000, 15, 'NEW'),
            ('Filtre à huile', 'oil', 'Denso', 3500, 50, 'NEW'),
            ('Ampoule H7', 'electrical', 'NGK', 2500, 30, 'NEW'),
            ('Amortisseur avant', 'suspension', 'KYB', 35000, 8, 'NEW'),
            ('Courroie trapézoïdale', 'engine', 'Gates', 8000, 20, 'NEW'),
            ('Ventilateur climatisation', 'ac', 'Denso', 45000, 5, 'NEW'),
        ]
        for name, cat_slug, brand_name, price, stock, condition in parts_data:
            Part.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'seller': client,
                    'category': categories[cat_slug],
                    'brand': brands[brand_name],
                    'garage': garage,
                    'name': name,
                    'description': f'{name} de qualité professionnelle',
                    'condition': condition,
                    'price': price,
                    'stock': stock,
                    'stock_status': Part.StockStatus.IN_STOCK,
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS('Données de démonstration créées avec succès !'))
