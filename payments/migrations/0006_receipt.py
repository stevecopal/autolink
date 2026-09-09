import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("garages", "0002_add_missing_fields"),
        ("payments", "0005_alter_payment_provider"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Receipt",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "reference",
                    models.CharField(editable=False, max_length=40, unique=True),
                ),
                ("amount", models.DecimalField(decimal_places=0, max_digits=10)),
                ("currency", models.CharField(default="XAF", max_length=3)),
                ("provider", models.CharField(max_length=20)),
                ("status", models.CharField(max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "garage",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="receipts",
                        to="garages.garage",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payment_receipts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receipt",
                        to="payments.payment",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
