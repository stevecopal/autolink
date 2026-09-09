from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0004_payment_provider_transaction_unique")]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(
                choices=[
                    ("PAYUNIT", "PayUnit"),
                    ("CAMPAY", "CamPay"),
                    ("MTN_MOMO", "MTN Mobile Money"),
                    ("ORANGE_MONEY", "Orange Money"),
                    ("CARD", "Carte bancaire"),
                    ("CASH", "Espèces"),
                ],
                max_length=20,
            ),
        ),
    ]
