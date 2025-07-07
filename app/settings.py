"""
Django settings for app project.

Optimized for Docker environments.
Reads configuration directly from environment variables.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ (ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ)
# ==============================================================================

SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', '0') == '1'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# ==============================================================================
# ПРИЛОЖЕНИЯ (APPLICATIONS)
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Для корректной работы с runserver в режиме DEBUG=True
    'django.contrib.staticfiles',
    'django.contrib.gis',

    # Сторонние приложения
    'rest_framework',
    'rest_framework_gis',
    'corsheaders',

    # Ваши приложения
    'geoclient',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise Middleware должен быть здесь, на втором месте.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'client' / 'dist',
        ],
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

WSGI_APPLICATION = 'app.wsgi.application'


# ==============================================================================
# БАЗА ДАННЫХ (DATABASE)
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}


# ==============================================================================
# ПАРОЛИ И ИНТЕРНАЦИОНАЛИЗАЦИЯ
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==============================================================================
# СТАТИЧЕСКИЕ И МЕДИА ФАЙЛЫ
# ==============================================================================

# Базовый URL для статики. Он ДОЛЖЕН БЫТЬ '/'.
STATIC_URL = '/static/'

# Папка, куда `collectstatic` собирает всю статику для продакшена.
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Источники статических файлов (откуда `collectstatic` будет их брать).
STATICFILES_DIRS = [
    BASE_DIR / 'client' / 'dist',
]

# Явно указываем WhiteNoise, что корень нашего SPA-приложения (index.html)
# и все его ассеты (JS, CSS) лежат в этой директории.
# WhiteNoise будет искать файлы здесь в первую очередь.
WHITENOISE_ROOT = BASE_DIR / 'client' / 'dist'

# Движок для хранения. Это включает сжатие и кэширование.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Настройки для медиа-файлов остаются без изменений
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'


# ==============================================================================
# НАСТРОЙКИ CORS и CSRF
# ==============================================================================

_csrf_trusted_origins_str = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = _csrf_trusted_origins_str.split(',') if _csrf_trusted_origins_str else []

_cors_allowed_origins_str = os.environ.get('CORS_ALLOWED_ORIGINS', '')
CORS_ALLOWED_ORIGINS = _cors_allowed_origins_str.split(',') if _cors_allowed_origins_str else []

if os.environ.get('CORS_ALLOW_ALL_ORIGINS') == '1':
    CORS_ALLOW_ALL_ORIGINS = True


# ==============================================================================
# ПРОЧИЕ НАСТРОЙКИ
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_NUMBER_FILES = 300