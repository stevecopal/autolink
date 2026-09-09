from django.db import migrations, models
import django.db.models.deletion
import support.models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='category',
        ),
        migrations.AddField(
            model_name='ticket',
            name='evidence',
            field=models.FileField(
                blank=True,
                help_text='Image ou fichier max 5 Mo (JPG, PNG, GIF, WebP, PDF, Word)',
                null=True,
                upload_to='tickets/evidence/',
                validators=[support.models.validate_evidence_file],
                verbose_name='Preuve',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='order',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tickets',
                to='orders.order',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='garage',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tickets',
                to='garages.garage',
            ),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('OPEN', 'Ouvert'),
                    ('IN_PROGRESS', 'En cours'),
                    ('RESOLVED', 'Résolu'),
                    ('CLOSED', 'Fermé'),
                ],
                default='OPEN',
                max_length=30,
            ),
        ),
    ]
