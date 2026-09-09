from django.db import migrations, models


def empty_transaction_ids_to_null(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    Payment.objects.filter(provider_transaction_id="").update(
        provider_transaction_id=None
    )


class Migration(migrations.Migration):
    dependencies = [("payments", "0003_payment_order_nullable")]

    operations = [
        migrations.RunPython(empty_transaction_ids_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="provider_transaction_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
