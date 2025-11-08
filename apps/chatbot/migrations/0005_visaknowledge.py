from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chatbot", "0004_userpreference"),
    ]

    operations = [
        migrations.CreateModel(
            name="VisaKnowledge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country", models.CharField(max_length=120)),
                ("visa_type", models.CharField(blank=True, max_length=120)),
                ("summary", models.TextField(blank=True)),
                ("requirements", models.JSONField(blank=True, null=True)),
                ("processing_time", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("source_url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["country", "visa_type"],
                "unique_together": {("country", "visa_type")},
            },
        ),
    ]

