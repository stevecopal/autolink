# Generated manually — données GPS officielles des villes camerounaises
from django.db import migrations


CITY_COORDS = {
    "Douala":     (4.0511,  9.7679),
    "Yaoundé":    (3.8480,  11.5021),
    "Bafoussam":  (5.4781,  10.4176),
    "Bamenda":    (5.9631,  10.1591),
    "Garoua":     (9.3017,  13.3977),
    "Maroua":     (10.5910, 14.3159),
    "Ngaoundéré": (7.3167,  13.5833),
    "Bertoua":    (4.5773,  13.6846),
    "Buea":       (4.1527,  9.2410),
    "Limbé":      (4.0186,  9.2103),
    "Kribi":      (2.9372,  9.9076),
    "Ebolowa":    (2.9000,  11.1500),
    "Edéa":       (3.8000,  10.1333),
    "Dschang":    (5.4500,  10.0500),
    "Nkongsamba": (4.9500,  9.9333),
}


def load_city_coordinates(apps, schema_editor):
    City = apps.get_model("core", "City")
    for name, (lat, lng) in CITY_COORDS.items():
        affected = City.objects.filter(name=name).update(latitude=lat, longitude=lng)
        # Silencieux — pas de print()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_remove_testimonial_content"),
    ]

    operations = [
        migrations.RunPython(load_city_coordinates, migrations.RunPython.noop),
    ]

