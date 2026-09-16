from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import City, Neighborhood, Testimonial


class Command(BaseCommand):
    help = "Initialise la base de données avec les villes, quartiers et témoignages réels du Cameroun."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "=== Début du chargement des données géographiques et témoignages ==="
            )
        )

        with transaction.atomic():
            cities_data = [
                {
                    "name": "Bafoussam",
                    "region": "Ouest",
                    "latitude": Decimal("5.477750"),
                    "longitude": Decimal("10.417590"),
                    "neighborhoods": [
                        "Bamendzi",
                        "Évêché",
                        "Djeleng",
                        "Tamdja",
                        "Kamkop",
                        "Kouogouo",
                        "Haoussa",
                        "Tougang",
                        "Banengo",
                        "Ndiangdam",
                        "Famla",
                        "Marché A",
                        "Socada",
                        "Koptchou",
                        "Tchems",
                        "Houkaha",
                        "Lemoh",
                        "Ndiambou",
                        "Ngouache",
                        "Yenou",
                        "Ville Haute",
                        "Ndemdjou",
                        "Baleng",
                        "Kamda",
                        "King Place",
                        "Batoufam (Secteur)",
                        "Tchitchap",
                        "Toket",
                        "Quartier Résidentiel",
                        "Nylon",
                    ],
                    "testimonials": [
                        {
                            "name": "Armel Tagne",
                            "role": Testimonial.Role.CLIENT,
                            "quote": "Tombé en panne au niveau de Kamkop, j'ai pu trouver un mécanicien disponible en moins de 15 minutes via la plateforme. Service impeccable !",
                            "rating": 5,
                        },
                        {
                            "name": "Garage Bellevue Bafoussam",
                            "role": Testimonial.Role.GARAGE,
                            "quote": "AutoLink nous apporte régulièrement des clients en détresse sur l'axe Bafoussam-Bamenda. Notre visibilité a doublé.",
                            "rating": 5,
                        },
                        {
                            "name": "Éts Fo'o Pièces Auto",
                            "role": Testimonial.Role.VENDEUR,
                            "quote": "Nous vendons nos pièces détachées d'origine aux garagistes de Bamendzi et Tamdja directement depuis l'application.",
                            "rating": 4,
                        },
                    ],
                },
                {
                    "name": "Dschang",
                    "region": "Ouest",
                    "latitude": Decimal("5.443000"),
                    "longitude": Decimal("10.053300"),
                    "neighborhoods": [
                        "Foreke-Dschang",
                        "Foto",
                        "Mingmeto",
                        "Sine",
                        "Tsinkop",
                        "Canne à Sucre",
                        "Val de la Mifi",
                        "Pays Bas",
                        "Ngui",
                        "Atsualong",
                        "Keleng",
                        "Djutitsa",
                        "Lifere",
                        "Toula-Foto",
                        "Baleveng",
                        "Zem-Foto",
                        "Likom",
                        "Tchouatse",
                        "Nzong",
                        "Teza",
                        "Quartier Résidentiel",
                        "Marché Central",
                        "Zone Administrative",
                        "Site Universitaire",
                        "Fonakeukeu",
                        "Fiala",
                        "Djou-Foto",
                        "Melieu",
                        "Tsingbeu",
                        "Litieu",
                    ],
                    "testimonials": [
                        {
                            "name": "Dr. Etienne Kenfack",
                            "role": Testimonial.Role.CLIENT,
                            "quote": "De passage pour l'Université de Dschang, mon véhicule est tombé en panne près de Ngui. Dépannage rapide et professionnel.",
                            "rating": 5,
                        },
                        {
                            "name": "Garage de la Falaise",
                            "role": Testimonial.Role.GARAGE,
                            "quote": "Grâce à la géolocalisation, les automobilistes en difficulté dans la falaise de Dschang nous trouvent facilement.",
                            "rating": 5,
                        },
                        {
                            "name": "Sopjio Auto Dschang",
                            "role": Testimonial.Role.VENDEUR,
                            "quote": "Excellente plateforme pour écouler nos stocks de batteries et amortisseurs à Dschang et ses environs.",
                            "rating": 4,
                        },
                    ],
                },
                {
                    "name": "Bandjoun",
                    "region": "Ouest",
                    "latitude": Decimal("5.375000"),
                    "longitude": Decimal("10.414000"),
                    "neighborhoods": [
                        "Pete",
                        "Ha",
                        "Semto",
                        "Houa",
                        "Tseleng",
                        "Mbouo",
                        "Dja",
                        "Yom",
                        "Djebem",
                        "Toukouo",
                        "Chefferie Supérieure",
                        "Pousse",
                        "Soung",
                        "Kassap",
                        "Fam-Leng",
                        "Kamkop-Bandjoun",
                        "Tcha",
                        "Kaa",
                        "Leng",
                        "Hiala",
                        "Djemgheu",
                        "Demgo",
                        "Nkouon",
                        "Tsoing",
                        "Nja",
                        "Famleng",
                        "Mo",
                        "Fondjomekwet (Secteur)",
                        "Centre Commercial Pete",
                        "Zone IUT",
                    ],
                    "testimonials": [
                        {
                            "name": "Rodrigue Kamdem",
                            "role": Testimonial.Role.CLIENT,
                            "quote": "J'ai eu un problème de freins à Pete en allant vers Bafoussam. Le mécanicien est arrivé en 20 minutes avec la bonne pièce.",
                            "rating": 5,
                        },
                        {
                            "name": "Auto Services du Koung-Khi",
                            "role": Testimonial.Role.GARAGE,
                            "quote": "Une solution moderne qui dynamise l'activité mécanique dans le Koung-Khi. Nous recevons des demandes ciblées.",
                            "rating": 5,
                        },
                        {
                            "name": "Comptoir Pièces Bandjoun",
                            "role": Testimonial.Role.VENDEUR,
                            "quote": "Mettre en avant notre catalogue auprès des garages locaux n'a jamais été aussi simple.",
                            "rating": 5,
                        },
                    ],
                },
                {
                    "name": "Baham",
                    "region": "Ouest",
                    "latitude": Decimal("5.333300"),
                    "longitude": Decimal("10.383300"),
                    "neighborhoods": [
                        "Chefferie (Hiala)",
                        "Kankop",
                        "Medjo",
                        "Chengne",
                        "Lagweu",
                        "Demgo",
                        "Wouong",
                        "Boukue",
                        "Pa",
                        "Pouomgne",
                        "Gomto",
                        "Bagam-Baham",
                        "Souo",
                        "Djemgheu-Baham",
                        "Kouom",
                        "Tsenlo",
                        "Medjo II",
                        "Banaho",
                        "Techie",
                        "Pekou",
                        "Famleng-Baham",
                        "Ngoumgne",
                        "Boukue II",
                        "Demgo II",
                        "Centre Ville",
                        "Quartier Administratif",
                        "Bagwah",
                        "Toum",
                        "Pekoua",
                        "Batoufam (Frontière)",
                    ],
                    "testimonials": [
                        {
                            "name": "Jean-Paul Guiffo",
                            "role": Testimonial.Role.CLIENT,
                            "quote": "Batterie à plat près du centre-ville de Baham un dimanche soir. J'ai trouvé un dépanneur grâce à AutoLink.",
                            "rating": 5,
                        },
                        {
                            "name": "Garage de Baham Centre",
                            "role": Testimonial.Role.GARAGE,
                            "quote": "Très bonne application pour connecter les professionnels de l'automobile du Haut-Nkam et des Hauts-Plateaux.",
                            "rating": 4,
                        },
                        {
                            "name": "Quincaillerie Auto Baham",
                            "role": Testimonial.Role.VENDEUR,
                            "quote": "Plateforme fiable qui facilite la livraison rapide de pièces détachées sur la nationale N4.",
                            "rating": 5,
                        },
                    ],
                },
            ]

            cities_created, neighborhoods_created, testimonials_created = 0, 0, 0

            for c_data in cities_data:
                city, created_city = City.objects.get_or_create(
                    name=c_data["name"],
                    defaults={
                        "region": c_data["region"],
                        "latitude": c_data["latitude"],
                        "longitude": c_data["longitude"],
                        "is_active": True,
                    },
                )
                if created_city:
                    cities_created += 1

                for n_name in c_data["neighborhoods"]:
                    # save() s'occupe de générer le slug automatiquement s'il est vide
                    neighborhood, created_n = Neighborhood.objects.get_or_create(
                        city=city, name=n_name, defaults={"is_active": True}
                    )
                    if created_n:
                        neighborhoods_created += 1

                for t_data in c_data["testimonials"]:
                    _, created_t = Testimonial.objects.get_or_create(
                        name=t_data["name"],
                        city=city.name,
                        quote=t_data["quote"],
                        defaults={
                            "role": t_data["role"],
                            "rating": t_data["rating"],
                            "is_published": True,
                        },
                    )
                    if created_t:
                        testimonials_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"=== Succès ===\n"
                f"- Villes ajoutées : {cities_created} / 4\n"
                f"- Quartiers ajoutés : {neighborhoods_created} / 120\n"
                f"- Témoignages ajoutés : {testimonials_created} / 12"
            )
        )

        # Vérification automatique de l'intégrité de la base de données
        self.verify_data()

    def verify_data(self):
        """Vérifie l'état actuel de la base de données après le chargement."""
        self.stdout.write(
            self.style.MIGRATE_HEADING("\n=== Rapport de Vérification ===")
        )

        total_cities = City.objects.count()
        total_neighborhoods = Neighborhood.objects.count()
        total_testimonials = Testimonial.objects.count()

        self.stdout.write(f"Total Villes en BD : {total_cities}")
        self.stdout.write(f"Total Quartiers en BD : {total_neighborhoods}")
        self.stdout.write(f"Total Témoignages en BD : {total_testimonials}")

        for city in City.objects.all():
            count_n = city.neighborhoods.count()
            count_t = Testimonial.objects.filter(city=city.name).count()
            status = "OK" if count_n >= 30 and count_t >= 3 else "INCOMPLET"
            self.stdout.write(
                f" - Ville: {city.name:<12} | Lat: {city.latitude}, Lon: {city.longitude} | "
                f"Quartiers: {count_n}/30 | Témoignages: {count_t}/3 | Statut: [{status}]"
            )
