from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.tour.models import TourPackage
from apps.visa.models import VisaRequest

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with realistic test data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to seed data...'))

        # Create users
        admin_user = self.create_admin_user()
        agency_users = self.create_agency_users()
        traveler_users = self.create_traveler_users()

        # Create tour packages for agencies
        self.create_tour_packages(agency_users)

        # Create visa requests for travelers
        self.create_visa_requests(traveler_users)

        self.stdout.write(self.style.SUCCESS('Successfully seeded all data!'))

    def create_admin_user(self):
        """Create admin user if it doesn't exist."""
        username = 'admin'
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Skipping...'))
            return User.objects.get(username=username)

        admin = User.objects.create_user(
            username=username,
            email='admin@tourbot.com',
            password='admin123',
            role='admin',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))
        return admin

    def create_agency_users(self):
        """Create agency users if they don't exist."""
        agencies = []
        agency_data = [
            {
                'username': 'agency1',
                'email': 'agency1@tourbot.com',
                'first_name': 'Agency',
                'last_name': 'One',
                'company_name': 'Travel Adventures Inc.',
            },
            {
                'username': 'agency2',
                'email': 'agency2@tourbot.com',
                'first_name': 'Agency',
                'last_name': 'Two',
                'company_name': 'World Tours Ltd.',
            },
        ]

        for data in agency_data:
            username = data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Skipping...'))
                agencies.append(User.objects.get(username=username))
            else:
                agency = User.objects.create_user(
                    username=username,
                    email=data['email'],
                    password='agency123',
                    role='agency',
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    company_name=data['company_name'],
                )
                self.stdout.write(self.style.SUCCESS(f'Created agency user: {username}'))
                agencies.append(agency)

        return agencies

    def create_traveler_users(self):
        """Create traveler users if they don't exist."""
        travelers = []
        traveler_data = [
            {
                'username': 'traveler1',
                'email': 'traveler1@tourbot.com',
                'first_name': 'John',
                'last_name': 'Doe',
            },
            {
                'username': 'traveler2',
                'email': 'traveler2@tourbot.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
            },
            {
                'username': 'traveler3',
                'email': 'traveler3@tourbot.com',
                'first_name': 'Bob',
                'last_name': 'Johnson',
            },
        ]

        for data in traveler_data:
            username = data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Skipping...'))
                travelers.append(User.objects.get(username=username))
            else:
                traveler = User.objects.create_user(
                    username=username,
                    email=data['email'],
                    password='traveler123',
                    role='traveler',
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                )
                self.stdout.write(self.style.SUCCESS(f'Created traveler user: {username}'))
                travelers.append(traveler)

        return travelers

    def create_tour_packages(self, agency_users):
        """Create tour packages for each agency."""
        tour_templates = [
            {
                'title': 'Paris City Break',
                'description': 'Experience the romance and charm of Paris with our 4-day city break. Visit the Eiffel Tower, Louvre Museum, and enjoy authentic French cuisine.',
                'destination_country': 'France',
                'price': 899.99,
            },
            {
                'title': 'Tokyo Cultural Experience',
                'description': 'Immerse yourself in Japanese culture with visits to ancient temples, traditional gardens, and modern districts. Includes guided tours and cultural workshops.',
                'destination_country': 'Japan',
                'price': 1299.99,
            },
            {
                'title': 'Safari Adventure in Kenya',
                'description': 'Witness the Big Five on an unforgettable safari adventure. Includes game drives, accommodation in luxury lodges, and expert guides.',
                'destination_country': 'Kenya',
                'price': 2499.99,
            },
        ]

        for agency in agency_users:
            for i, template in enumerate(tour_templates):
                # Create unique title for each agency
                title = f"{template['title']} - {agency.company_name or agency.username}"
                
                # Check if this specific tour already exists
                tour, created = TourPackage.objects.get_or_create(
                    title=title,
                    defaults={
                        'user': agency,
                        'description': template['description'],
                        'destination_country': template['destination_country'],
                        'start_date': timezone.now().date() + timedelta(days=30 + (i * 10)),
                        'end_date': timezone.now().date() + timedelta(days=34 + (i * 10)),
                        'price': template['price'],
                        'is_active': True,
                    }
                )
                
                # If tour exists but doesn't have a user assigned, update it
                if not created and not tour.user:
                    tour.user = agency
                    tour.save()
                    self.stdout.write(self.style.SUCCESS(f'Updated tour package: {title} (assigned to {agency.username})'))
                elif created:
                    self.stdout.write(self.style.SUCCESS(f'Created tour package: {title}'))

    def create_visa_requests(self, traveler_users):
        """Create visa requests for each traveler."""
        destinations = [
            {'country': 'France', 'status': 'pending'},
            {'country': 'Japan', 'status': 'approved'},
        ]

        for traveler in traveler_users:
            # Check if traveler already has visa requests
            existing_requests = VisaRequest.objects.filter(user=traveler).count()
            if existing_requests >= len(destinations):
                self.stdout.write(self.style.WARNING(f'Visa requests for {traveler.username} already exist. Skipping...'))
                continue

            for i, dest in enumerate(destinations):
                # Check if this specific request already exists
                if VisaRequest.objects.filter(
                    user=traveler,
                    destination_country=dest['country']
                ).exists():
                    continue

                travel_date = timezone.now().date() + timedelta(days=60 + (i * 15))

                VisaRequest.objects.create(
                    user=traveler,
                    full_name=f"{traveler.first_name} {traveler.last_name}",
                    passport_number=f"P{traveler.id:06d}",
                    nationality='United States',
                    destination_country=dest['country'],
                    travel_date=travel_date,
                    status=dest['status'],
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created visa request for {traveler.username}: {dest["country"]} ({dest["status"]})'
                    )
                )

