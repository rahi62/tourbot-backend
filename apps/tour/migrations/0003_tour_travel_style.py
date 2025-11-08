from django.db import migrations, models

import apps.tour.constants


class Migration(migrations.Migration):

    dependencies = [
        ("tour", "0002_tourpackage_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="tour",
            name="travel_style",
            field=models.CharField(
                choices=apps.tour.constants.TRAVEL_STYLE_CHOICES,
                default="general",
                max_length=20,
            ),
        ),
    ]


