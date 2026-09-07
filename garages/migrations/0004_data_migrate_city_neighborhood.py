from django.db import migrations


class Migration(migrations.Migration):
    """
    La migration du schéma 0003 convertit déjà les champs city/neighborhood
    de CharField en ForeignKey. Les données existantes doivent être gérées
    manuellement ou via le management command seed_data.
    """

    dependencies = [
        ('garages', '0003_remove_garage_cover_photo_remove_garage_logo_and_more'),
        ('core', '0002_city_neighborhood'),
    ]

    operations = []
