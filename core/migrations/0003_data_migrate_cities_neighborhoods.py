from django.db import migrations


def create_initial_cities_and_neighborhoods(apps, schema_editor):
    City = apps.get_model('core', 'City')
    Neighborhood = apps.get_model('core', 'Neighborhood')

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

    for city_name, neighborhoods in cities_data.items():
        slug = city_name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
        city, _ = City.objects.get_or_create(
            slug=slug,
            defaults={'name': city_name}
        )
        for n_name in neighborhoods:
            n_slug = n_name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
            Neighborhood.objects.get_or_create(
                city=city,
                slug=n_slug,
                defaults={'name': n_name}
            )


def migrate_garage_city_neighborhood_to_fk(apps, schema_editor):
    """Convert string city/neighborhood to FK references."""
    City = apps.get_model('core', 'City')
    Neighborhood = apps.get_model('core', 'Neighborhood')
    Garage = apps.get_model('garages', 'Garage')

    for garage in Garage.objects.all():
        if garage.city and isinstance(garage.city, str):
            city_slug = garage.city.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
            try:
                city = City.objects.get(slug=city_slug)
                garage.city_id = city.pk
                garage.save(update_fields=['city_id'])
            except City.DoesNotExist:
                pass

        if garage.neighborhood and isinstance(garage.neighborhood, str):
            n_slug = garage.neighborhood.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')
            if garage.city_id:
                try:
                    city = City.objects.get(pk=garage.city_id)
                    neighborhood = Neighborhood.objects.get(city=city, slug=n_slug)
                    garage.neighborhood_id = neighborhood.pk
                    garage.save(update_fields=['neighborhood_id'])
                except (City.DoesNotExist, Neighborhood.DoesNotExist):
                    pass


def migrate_user_roles(apps, schema_editor):
    """Promote users who have at least one approved garage to CLIENT."""
    User = apps.get_model('accounts', 'User')
    Garage = apps.get_model('garages', 'Garage')

    for user in User.objects.all():
        has_approved = Garage.objects.filter(
            owner=user,
            verification_status='APPROVED',
            is_active=True
        ).exists()
        if has_approved and user.role != 'ADMIN':
            user.role = 'CLIENT'
            user.save(update_fields=['role'])


def reverse_migrate_user_roles(apps, schema_editor):
    """Revert CLIENT users with no garages back to USER."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_city_neighborhood'),
        ('accounts', '0002_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(create_initial_cities_and_neighborhoods, migrations.RunPython.noop),
        migrations.RunPython(migrate_user_roles, reverse_migrate_user_roles),
    ]
