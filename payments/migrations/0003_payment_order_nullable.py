import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_payment_garage")]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="orders.order",
            ),
        ),
    ]
