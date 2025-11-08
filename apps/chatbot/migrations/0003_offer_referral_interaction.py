from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chatbot", "0002_chatlead_chatinteraction"),
    ]

    operations = [
        migrations.CreateModel(
            name="Offer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("destination", models.CharField(blank=True, max_length=120)),
                (
                    "service_type",
                    models.CharField(
                        choices=[("tour", "Tour"), ("visa", "Visa")],
                        default="tour",
                        max_length=20,
                    ),
                ),
                ("is_premium", models.BooleanField(default=False)),
                ("premium_type", models.CharField(blank=True, max_length=50)),
                ("price_cents", models.PositiveIntegerField(default=0)),
                ("image_url", models.URLField(blank=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Referral",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(editable=False, max_length=20, unique=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_referrals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referrals",
                        to="chatbot.offer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Interaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event",
                    models.CharField(
                        choices=[
                            ("impression", "Impression"),
                            ("click", "Click"),
                            ("checkout_start", "Checkout Start"),
                            ("payment_success", "Payment Success"),
                            ("payment_failed", "Payment Failed"),
                        ],
                        max_length=32,
                    ),
                ),
                ("session_id", models.CharField(blank=True, max_length=64)),
                ("referral_code", models.CharField(blank=True, max_length=20)),
                ("payload", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "offer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interactions",
                        to="chatbot.offer",
                    ),
                ),
                (
                    "referral",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interactions",
                        to="chatbot.referral",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="offer_interactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]

