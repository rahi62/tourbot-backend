"""
Django settings for tourbot_backend project.
Environment-based configuration with development and production modes.
"""

from pathlib import Path
from datetime import timedelta
import os
from decouple import config, Csv
import dj_database_url
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Default to True for development if not explicitly set
DEBUG = config('DEBUG', default=True, cast=bool)

# Frontend URL for CORS configuration
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# ============================================================================
# DEVELOPMENT vs PRODUCTION SETTINGS
# ============================================================================

if DEBUG:
    # ========================================================================
    # DEVELOPMENT SETTINGS
    # ========================================================================
    
    # Allow all hosts in development
    ALLOWED_HOSTS = ['*']
    
    # Database - Use SQLite for development (or local PostgreSQL)
    DATABASE_URL = config('DATABASE_URL', default=None)
    if DATABASE_URL:
        # Use DATABASE_URL if provided
        DATABASES = {
            'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
        }
    else:
        # Fallback to SQLite for easy local development
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }
        # Or use local PostgreSQL if preferred:
        # DATABASES = {
        #     'default': {
        #         'ENGINE': 'django.db.backends.postgresql',
        #         'NAME': config('DB_NAME', default='tourbot_db'),
        #         'USER': config('DB_USER', default='postgres'),
        #         'PASSWORD': config('DB_PASSWORD', default='postgres'),
        #         'HOST': config('DB_HOST', default='localhost'),
        #         'PORT': config('DB_PORT', default='5432'),
        #     }
        # }
    
    # CORS - Allow localhost and mobile devices in development
    # For mobile testing, you can use your computer's IP address
    # Example: http://192.168.1.100:3000 (replace with your actual IP)
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://192.168.1.100:3000',
        'http://127.0.0.1:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3001',
    ]
    
    # Allow all origins in development for easier mobile testing
    # Set CORS_ALLOW_ALL_ORIGINS=True in .env to enable this
    # WARNING: Only use in development, never in production!
    if config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool):
        CORS_ALLOW_ALL_ORIGINS = True
    else:
        # Get IP address for mobile access on same network
        import socket
        try:
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Add IP-based origins for mobile access
            CORS_ALLOWED_ORIGINS.extend([
                f'http://{local_ip}:3000',
                f'http://{local_ip}:3001',
            ])
        except Exception:
            pass  # If can't get IP, just use localhost origins
    
    # Logging - Verbose logging for development
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }
    
    # Don't use WhiteNoise in development (Django serves static files)
    USE_WHITENOISE = False
    
else:
    # ========================================================================
    # PRODUCTION SETTINGS
    # ========================================================================
    
    # Restrict allowed hosts in production
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())
    if not ALLOWED_HOSTS:
        raise ValueError('ALLOWED_HOSTS must be set in production!')
    
    # Database - Must use DATABASE_URL in production
    DATABASE_URL = config('DATABASE_URL', default=None)
    if not DATABASE_URL:
        raise ValueError('DATABASE_URL must be set in production!')
    
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
    
    # CORS - Use FRONTEND_URL or CORS_ALLOWED_ORIGINS from environment
    cors_origins = config('CORS_ALLOWED_ORIGINS', default=None, cast=Csv())
    if cors_origins:
        CORS_ALLOWED_ORIGINS = cors_origins
    elif FRONTEND_URL:
        CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
    else:
        raise ValueError('CORS_ALLOWED_ORIGINS or FRONTEND_URL must be set in production!')
    
    # Logging - Production logging (less verbose)
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }
    
    # Use WhiteNoise for static files in production
    USE_WHITENOISE = True
    
    # Security settings for production
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'apps.accounts',
    'apps.visa',
    'apps.tour',
    'apps.chatbot',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]

# Conditionally add WhiteNoise middleware
if USE_WHITENOISE:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')

MIDDLEWARE.extend([
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])

ROOT_URLCONF = 'tourbot_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tourbot_backend.wsgi.application'

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC FILES & MEDIA
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration (only used in production)
if USE_WHITENOISE:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# DJANGO REST FRAMEWORK
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

# ============================================================================
# SIMPLE JWT SETTINGS
# ============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ============================================================================
# CORS SETTINGS
# ============================================================================

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================================================
# OPENAI API KEY
# ============================================================================

OPENAI_API_KEY = config('OPENAI_API_KEY', default=None)
