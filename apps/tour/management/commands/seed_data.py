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
            first_name='مدیر',
            last_name='کل',
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
                'username': 'agency_tehran',
                'email': 'agency_tehran@tourbot.com',
                'first_name': 'آژانس',
                'last_name': 'تهران',
                'company_name': 'آژانس سفر تهران',
            },
            {
                'username': 'agency_iraniyan',
                'email': 'agency_iraniyan@tourbot.com',
                'first_name': 'آژانس',
                'last_name': 'ایرانیان',
                'company_name': 'ایرانیان گردشگری',
            },
            {
                'username': 'agency_shomal',
                'email': 'agency_shomal@tourbot.com',
                'first_name': 'آژانس',
                'last_name': 'شمال',
                'company_name': 'سفرهای سرزمین شمال',
            },
            {
                'username': 'agency_parvaz',
                'email': 'agency_parvaz@tourbot.com',
                'first_name': 'آژانس',
                'last_name': 'پرواز',
                'company_name': 'آسمان آبی پرواز',
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
                'username': 'mosafir_ali',
                'email': 'ali.mosafir@tourbot.com',
                'first_name': 'علی',
                'last_name': 'مسافر',
            },
            {
                'username': 'mosafir_sara',
                'email': 'sara.mosafir@tourbot.com',
                'first_name': 'سارا',
                'last_name': 'جهانگرد',
            },
            {
                'username': 'mosafir_mahdi',
                'email': 'mahdi.mosafir@tourbot.com',
                'first_name': 'مهدی',
                'last_name': 'سیاح',
            },
            {
                'username': 'mosafir_nazanin',
                'email': 'nazanin.mosafir@tourbot.com',
                'first_name': 'نازنین',
                'last_name': 'گردشگر',
            },
            {
                'username': 'mosafir_reza',
                'email': 'reza.mosafir@tourbot.com',
                'first_name': 'رضا',
                'last_name': 'جهانگرد',
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
                    password='user123',
                    role='traveler',
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                )
                self.stdout.write(self.style.SUCCESS(f'Created traveler user: {username}'))
                travelers.append(traveler)

        return travelers

    def create_tour_packages(self, agency_users):
        """Create tour packages for each agency."""
        TourPackage.objects.all().delete()

        tour_templates = [
            {
                'title': 'تور نوروزی استانبول',
                'description': '۵ شب و ۶ روز اقامت در هتل چهارستاره با صبحانه، گشت شهری و کشتی شبانگاهی بر روی بسفر.',
                'destination_country': 'ترکیه',
                'price': 18500000,
            },
            {
                'title': 'تور بهاری تفلیس و باتومی',
                'description': 'سفر ترکیبی ۶ روزه به تفلیس و باتومی همراه با گشت‌های اختصاصی و راهنمای فارسی‌زبان.',
                'destination_country': 'گرجستان',
                'price': 16200000,
            },
            {
                'title': 'تور دریایی کیش لوکس',
                'description': '۳ شب اقامت در هتل پنج‌ستاره ساحلی، تفریحات دریایی (پاراسل، فلای‌بورد) و گشت VIP جزیره.',
                'destination_country': 'ایران - کیش',
                'price': 9800000,
            },
            {
                'title': 'تور طبیعت‌گردی ماسال',
                'description': '۲ شب اقامت در کلبه‌های چوبی، بازدید از ییلاق اولسبلنگاه و صبحانه محلی.',
                'destination_country': 'ایران - گیلان',
                'price': 4800000,
            },
            {
                'title': 'تور لوکس دبی',
                'description': '۵ شب اقامت در هتل پنج‌ستاره، سافاری صحرایی، بازدید از اوتلت و مرکز خرید دبی مال.',
                'destination_country': 'امارات متحده عربی',
                'price': 28900000,
            },
            {
                'title': 'تور ساحلی آنتالیا',
                'description': '۶ شب اقامت فول‌برد در هتل آل، پارک آبی و تفریحات ساحلی رایگان.',
                'destination_country': 'ترکیه',
                'price': 21500000,
            },
            {
                'title': 'تور فرهنگی اصفهان و شیراز',
                'description': '۴ شب اقامت، بازدید از آثار تاریخی نقش جهان، تخت جمشید و مجموعه‌های مذهبی.',
                'destination_country': 'ایران',
                'price': 6500000,
            },
            {
                'title': 'تور طبیعت‌گردی کویر مرنجاب',
                'description': 'اقامت در کاروانسرای کویری، آفرود در شن‌های روان و رصد ستارگان.',
                'destination_country': 'ایران - کاشان',
                'price': 3600000,
            },
            {
                'title': 'تور خانوادگی استانبول + آنکارا',
                'description': '۷ روز سفر ترکیبی با پرواز مستقیم، هتل چهارستاره و گشت مراکز تاریخی.',
                'destination_country': 'ترکیه',
                'price': 24300000,
            },
            {
                'title': 'تور اقتصادی ایروان',
                'description': '۳ شب اقامت با صبحانه، گشت دریاچه سوان و بازدید از کارخانه براندی آرارات.',
                'destination_country': 'ارمنستان',
                'price': 11800000,
            },
            {
                'title': 'تور عاشقانه مالدیو',
                'description': '۴ شب اقامت در ویلا روی آب، سرویس ویژه ماه عسل و غواصی در صخره‌های مرجانی.',
                'destination_country': 'مالدیو',
                'price': 74500000,
            },
            {
                'title': 'تور طبیعت‌گردی کردستان',
                'description': '۳ روز اقامت در بومگردی، بازدید از اورامانات، آبشار بل و جشن شبانه کردی.',
                'destination_country': 'ایران - کردستان',
                'price': 5900000,
            },
            {
                'title': 'تور جزیره قشم و هرمز',
                'description': '۴ روز اقامت، بازدید از دره ستارگان، غار نمکدان و جزیره رنگارنگ هرمز.',
                'destination_country': 'ایران - قشم',
                'price': 8700000,
            },
            {
                'title': 'تور زمستانی استانبول برای خرید',
                'description': '۳ شب اقامت، ترنسفر فرودگاهی، کارت تخفیف مراکز خرید و تور شبانه.',
                'destination_country': 'ترکیه',
                'price': 15600000,
            },
            {
                'title': 'تور زمستانی دبی با جشن سال نو',
                'description': '۵ شب اقامت، جشن شب سال نو در برج خلیفه و بازدید از سرزمین برف.',
                'destination_country': 'امارات متحده عربی',
                'price': 31200000,
            },
            {
                'title': 'تور تاریخی یزد و کرمان',
                'description': '۴ روز سفر، اقامت در خانه‌های سنتی، بازدید از باغ دولت‌آباد و ارگ بم.',
                'destination_country': 'ایران',
                'price': 7200000,
            },
            {
                'title': 'تور لوکس قطر با جام ملت‌ها',
                'description': '۴ شب اقامت در هتل پنج‌ستاره، بلیت بازی‌های منتخب و گشت دوحه.',
                'destination_country': 'قطر',
                'price': 45500000,
            },
            {
                'title': 'تور بهاری شیراز و لارستان',
                'description': '۳ شب اقامت، بازدید از باغ ارم، پاسارگاد و بازار وکیل.',
                'destination_country': 'ایران - فارس',
                'price': 6400000,
            },
            {
                'title': 'تور زمستانی استانبول ویژه کریسمس',
                'description': '۵ شب اقامت، جشن کریسمس، گشت مراکز خرید و حمام سنتی ترکی.',
                'destination_country': 'ترکیه',
                'price': 23800000,
            },
            {
                'title': 'تور روسیه: مسکو و سنت پترزبورگ',
                'description': '۷ شب سفر، بازدید از میدان سرخ، کاخ کرملین و تئاتر باله.',
                'destination_country': 'روسیه',
                'price': 39800000,
            },
            {
                'title': 'تور سوئیس: زوریخ و لوسرن',
                'description': '۶ شب اقامت هتل چهارستاره، گشت دریاچه لوسرن و قطار پانوراما.',
                'destination_country': 'سوئیس',
                'price': 68500000,
            },
            {
                'title': 'تور عمان: مسقط و صلاله',
                'description': '۴ شب اقامت، گشت صلاله و بازدید از قصر العلم و بازار مطرح.',
                'destination_country': 'عمان',
                'price': 21900000,
            },
            {
                'title': 'تور استانبول با کنسرت ترکی',
                'description': '۳ شب اقامت، بلیت کنسرت، گشت بازار بزرگ و برج گالاتا.',
                'destination_country': 'ترکیه',
                'price': 18800000,
            },
            {
                'title': 'تور عمان ساحلی ویژه غواصی',
                'description': '۵ روز سفر، آموزش غواصی، اقامت ساحلی و کشتی تفریحی.',
                'destination_country': 'عمان',
                'price': 27600000,
            },
            {
                'title': 'تور بهاری لبنان: بیروت و بعلبک',
                'description': '۴ شب اقامت، بازدید از صخره‌های روشه و جشنواره غذاهای لبنانی.',
                'destination_country': 'لبنان',
                'price': 23500000,
            },
            {
                'title': 'تور طبیعت‌گردی کردان و طالقان',
                'description': '۲ شب اقامت در ویلاهای جنگلی، پیک‌نیک کنار رودخانه و دوچرخه‌سواری.',
                'destination_country': 'ایران - البرز',
                'price': 4200000,
            },
            {
                'title': 'تور فرهنگی تبریز و کندوان',
                'description': '۳ روز سفر، اقامت در کندوان، بازدید از ایل‌گلی و بازار تاریخی.',
                'destination_country': 'ایران - آذربایجان شرقی',
                'price': 6100000,
            },
            {
                'title': 'تور ایتالیا: رم و فلورانس',
                'description': '۷ شب، بازدید از کولوسئوم، واتیکان و کلاس آشپزی ایتالیایی.',
                'destination_country': 'ایتالیا',
                'price': 54500000,
            },
            {
                'title': 'تور اسپانیا: بارسلونا و مادرید',
                'description': '۶ شب اقامت، بازدید از ساگرادا فامیلیا و موزه پرادو.',
                'destination_country': 'اسپانیا',
                'price': 49800000,
            },
            {
                'title': 'تور فرانسه: پاریس با دیزنی‌لند',
                'description': '۵ شب اقامت، بلیت دیزنی‌لند، قایق‌سواری سن و بازدید از موزه لوور.',
                'destination_country': 'فرانسه',
                'price': 61200000,
            },
            {
                'title': 'تور چین: پکن و شانگهای',
                'description': 'هفت شب اقامت، بازدید از دیوار چین، شهر ممنوعه و برج شانگهای.',
                'destination_country': 'چین',
                'price': 45200000,
            },
        ]

        for index, template in enumerate(tour_templates):
            agency = agency_users[index % len(agency_users)]
            start_date = timezone.now().date() + timedelta(days=20 + index * 3)
            end_date = start_date + timedelta(days=4)

            is_featured = index % 5 in (0, 1)
            is_discounted = index % 4 == 0
            discount_percentage = None
            if is_discounted:
                discount_percentage = 10 + (index % 3) * 5

            TourPackage.objects.create(
                user=agency,
                title=f"{template['title']} - {agency.company_name or agency.username}",
                description=template["description"],
                destination_country=template["destination_country"],
                start_date=start_date,
                end_date=end_date,
                price=template["price"],
                is_active=True,
                is_featured=is_featured,
                is_discounted=is_discounted,
                discount_percentage=discount_percentage,
            )

        self.stdout.write(self.style.SUCCESS('Created 30 Persian tour packages.'))

    def create_visa_requests(self, traveler_users):
        """Create visa requests for each traveler."""
        destinations = [
            {'country': 'ترکیه', 'status': 'pending'},
            {'country': 'گرجستان', 'status': 'approved'},
        ]

        for traveler in traveler_users:
            for i, dest in enumerate(destinations):
                # Create unique passport number for each request
                passport_number = f"P{traveler.id:06d}{i+1}"
                full_name = f"{traveler.first_name} {traveler.last_name}"
                travel_date = timezone.now().date() + timedelta(days=60 + (i * 15))
                
                # Use get_or_create for idempotency - check by user, destination, and passport
                visa_request, created = VisaRequest.objects.get_or_create(
                    user=traveler,
                    passport_number=passport_number,
                    destination_country=dest['country'],
                    defaults={
                        'full_name': full_name,
                        'nationality': 'ایران',
                        'travel_date': travel_date,
                        'status': dest['status'],
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created visa request for {traveler.username}: {dest["country"]} ({dest["status"]})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Visa request for {traveler.username}: {dest["country"]} already exists. Skipping...'
                        )
                    )

