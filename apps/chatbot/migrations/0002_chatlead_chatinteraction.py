from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatLead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('phone', models.CharField(max_length=50)),
                ('type', models.CharField(choices=[('tour', 'Tour'), ('visa', 'Visa')], max_length=10)),
                ('destination', models.CharField(blank=True, max_length=160)),
                ('budget', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('travel_date', models.DateField(blank=True, null=True)),
                ('message', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_leads', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intent', models.CharField(choices=[('tour', 'Tour'), ('visa', 'Visa'), ('lead', 'Lead'), ('unknown', 'Unknown')], default='unknown', max_length=32)),
                ('raw_query', models.TextField()),
                ('extracted_data', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_interactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]


