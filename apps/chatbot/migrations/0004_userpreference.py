from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chatbot", "0003_offer_referral_interaction"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPreference",
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
                ("phone", models.CharField(blank=True, default="", max_length=20)),
                ("favorite_destinations", models.JSONField(blank=True, default=list)),
                (
                    "travel_style",
                    models.CharField(
                        choices=[
                            ("general", "عمومی"),
                            ("luxury", "لوکس"),
                            ("adventure", "ماجراجویی"),
                            ("cultural", "فرهنگی"),
                            ("family", "خانوادگی"),
                            ("nature", "طبیعت‌گردی"),
                            ("romantic", "ماه عسل / رمانتیک"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                ("budget_min", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("budget_max", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="chat_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="userpreference",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("user",),
                name="unique_user_preference",
            ),
        ),
        migrations.AddConstraint(
            model_name="userpreference",
            constraint=models.UniqueConstraint(
                condition=models.Q(("phone__gt", "")),
                fields=("phone",),
                name="unique_phone_preference",
            ),
        ),
    ]


