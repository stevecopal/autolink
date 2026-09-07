from django.core.management.base import BaseCommand
from django.utils.text import slugify
from accounts.models import User
from vehicles.models import Brand, ModelVehicle, Vehicle
from garages.models import Garage, GarageService
from catalog.models import Category, Part, Compatibility


class Command(BaseCommand):
    help = 'Peuple la base avec des données de démonstration'

    def handle(self, *args, **options):
        self.stdout.write('Création des données de démonstration...')

        # Create admin
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

        # Create client
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

        # Create garage owner
        garage_owner, _ = User.objects.get_or_create(
            username='garagiste1',
            defaults={
                'email': 'garage@example.com',
                'first_name': 'Paul',
                'last_name': 'Ngo',
                'phone': '+237690000002',
                'city': 'Douala',
                'neighborhood': 'Bonapriso',
                'role': 'GARAGE',
            }
        )
        garage_owner.set_password('garage123')
        garage_owner.save()

        # Brands
        brands_data = ['Toyota', 'Hyundai', 'Honda', 'Mercedes-Benz', 'BMW', 'Renault', 'Peugeot', 'Ford', 'Nissan', 'Kia', 'Bosch', 'NGK', 'Gates', 'KYB', 'Denso']
        brands = {}
        for name in brands_data:
            brand, _ = Brand.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name}
            )
            brands[name] = brand

        # Models
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

        # Client vehicle
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

        # Categories
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

        # Garage
        garage, _ = Garage.objects.get_or_create(
            slug=slugify('garage-autoplus'),
            defaults={
                'owner': garage_owner,
                'name': 'Garage AutoPlus',
                'description': 'Spécialiste Toyota et Hyundai. Diagnostic professionnel, entretien et réparation.',
                'phone': '+237690000010',
                'whatsapp': '237690000010',
                'address': 'Rue Joss, Bonapriso',
                'city': 'Douala',
                'neighborhood': 'Bonapriso',
                'latitude': 4.0185,
                'longitude': 9.6935,
                'verification_status': 'VERIFIED',
                'opening_time': '08:00',
                'closing_time': '18:00',
                'open_weekends': False,
                'trust_score': 4.7,
                'total_reviews': 42,
                'total_orders': 156,
                'total_clients': 89,
            }
        )

        # Services
        services_data = [
            ('Diagnostic moteur', 'DIAGNOSTIC', 5000, 15000),
            ('Vidange complète', 'OIL_CHANGE', 15000, 35000),
            ('Remplacement plaquettes', 'BRAKES', 10000, 25000),
            ('Réparation climatisation', 'AIR_CONDITIONING', 20000, 80000),
            ('Entretien périodique', 'MAINTENANCE', 25000, 60000),
        ]
        for name, cat, pmin, pmax in services_data:
            GarageService.objects.get_or_create(
                garage=garage,
                name=name,
                defaults={
                    'category': cat,
                    'price_min': pmin,
                    'price_max': pmax,
                }
            )

        # Parts
        parts_data = [
            ('Plaquettes de frein Bosch', categories['brakes'], brands['Bosch'], 25000, 8, '0986494387', 'Neuf'),
            ('Disques de frein avant', categories['brakes'], brands['Bosch'], 45000, 4, '0986AB1185', 'Neuf'),
            ('Filtre à huile Toyota', categories['oil'], brands['Toyota'], 8000, 25, '04152-31090', 'Neuf'),
            ('Filtre à air Toyota', categories['engine'], brands['Toyota'], 12000, 15, '17801-21050', 'Neuf'),
            ("Bougie d'allumage NGK", categories['electrical'], brands['NGK'], 5000, 30, 'BKR6E', 'Neuf'),
            ('Amortisseur avant KYB', categories['suspension'], brands['KYB'], 35000, 6, '339012', 'Neuf'),
            ('Courroie de distribution Gates', categories['engine'], brands['Gates'], 28000, 10, '94810-1210', 'Neuf'),
            ('Compresseur climatisation', categories['ac'], brands['Denso'], 120000, 2, '447220-4370', 'Reconditionné'),
        ]

        parts = {}
        for name, cat, brand_obj, price, stock, ref, condition in parts_data:

            part, _ = Part.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'seller': garage_owner,
                    'category': cat,
                    'name': name,
                    'brand': brand_obj,
                    'price': price,
                    'stock': stock,
                    'reference_oem': ref,
                    'condition': 'NEW' if condition == 'Neuf' else 'REFURBISHED',
                    'garage': garage,
                    'city': 'Douala',
                    'neighborhood': 'Bonapriso',
                }
            )
            parts[name] = part
            part.update_stock_status()

        # Compatibilities for Toyota parts
        toyota = brands['Toyota']
        corolla = vehicle_models[('Toyota', 'Corolla')]
        yaris = vehicle_models[('Toyota', 'Yaris')]

        for part_name in ['Plaquettes de frein Bosch', 'Filtre à huile Toyota', 'Filtre à air Toyota']:
            if part_name in parts:
                Compatibility.objects.get_or_create(
                    part=parts[part_name],
                    brand=toyota,
                    model_vehicle=corolla,
                    defaults={
                        'year_min': 2015,
                        'year_max': 2023,
                        'status': 'CONFIRMED',
                    }
                )
                Compatibility.objects.get_or_create(
                    part=parts[part_name],
                    brand=toyota,
                    model_vehicle=yaris,
                    defaults={
                        'year_min': 2010,
                        'year_max': 2023,
                        'status': 'CONFIRMED',
                    }
                )

        self.stdout.write(self.style.SUCCESS('Données de démonstration créées avec succès!'))
        self.stdout.write(f'Admin: admin / admin123')
        self.stdout.write(f'Client: client1 / client123')
        self.stdout.write(f'Garagiste: garagiste1 / garage123')
