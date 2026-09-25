# Generated manually for city choices and tenant filter expansion.

from django.db import migrations, models

import listings.choices


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0009_listing_tenant_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="city",
            field=models.CharField(
                choices=listings.choices.BANGLADESH_CITY_CHOICES,
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="tenant_type",
            field=models.CharField(
                choices=[
                    ("bachelor", "Bachelor"),
                    ("family", "Family"),
                    ("girl", "Girl"),
                    ("any", "Any"),
                ],
                db_index=True,
                default="any",
                help_text="Who this rental best suits: bachelor, family, girl, or any.",
                max_length=20,
            ),
        ),
    ]
