# app/settings.py

import os
import platform
from pathlib import Path

# ==============================================================================
# ОСНОВНЫЕ НАСТРОЙКИ
# ==============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-dev')
DEBUG = os.environ.get('DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,web').split(',')

DATA_UPLOAD_MAX_NUMBER_FILES = 300

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# ==============================================================================
# ПРИЛОЖЕНИЯ (APPLICATIONS)
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'rest_framework',
    'rest_framework_gis',
    'rest_framework.authtoken',
    'corsheaders',
    'django_vite',
    'geoclient.apps.GeoclientConfig',
]

# ==============================================================================
# MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

# ==============================================================================
# ШАБЛОНЫ (TEMPLATES)
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
        'ENGINE': os.environ.get('SQL_ENGINE', 'django.contrib.gis.db.backends.postgis'),
        'NAME': os.environ.get('DB_NAME', 'praktika'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '12345'),
        
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        
        'PORT': os.environ.get('DB_PORT', '5433'),
    }
}
# ==============================================================================
# ВАЛИДАЦИЯ ПАРОЛЕЙ
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================================================================
# ИНТЕРНАЦИОНАЛИЗАЦИЯ
# ==============================================================================
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# СТАТИЧЕСКИЕ И МЕДИА ФАЙЛЫ
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

STATICFILES_DIRS = [
    BASE_DIR / "client" / "dist",
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# НАСТРОЙКИ CORS (Cross-Origin Resource Sharing)
# ==============================================================================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# НАСТРОЙКИ DJANGO REST FRAMEWORK
# ==============================================================================
DEFAULT_RENDERERS = [
    'rest_framework.renderers.JSONRenderer',
]
if DEBUG:
    DEFAULT_RENDERERS.append('rest_framework.renderers.BrowsableAPIRenderer')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': DEFAULT_RENDERERS,
}

LOGIN_URL = 'admin:login'
LOGOUT_REDIRECT_URL = '/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# НАСТРОЙКИ DJANGO-VITE
# ==============================================================================
# --- ИСПРАВЛЕНИЕ: Используем правильные ключи dev_server_host и dev_server_port ---
DJANGO_VITE = {
    "default": {
        "manifest_path": BASE_DIR / "client" / "dist" / ".vite" / "manifest.json",
        
        "dev_mode": False, 
        
        "dev_server_host": "127.0.0.1",
        "dev_server_port": 5173,
    }
}

# ==============================================================================
# СПЕЦИФИЧНЫЕ ДЛЯ СИСТЕМЫ НАСТРОЙКИ (GDAL)
# ==============================================================================
if platform.system() == 'Windows':
    CONDA_BIN_PATH = r"C:\Users\iimin\miniconda3\Library\bin"
    if os.path.exists(CONDA_BIN_PATH):
        os.environ['PATH'] = CONDA_BIN_PATH + os.pathsep + os.environ.get('PATH', '')
        GDAL_LIBRARY_PATH = os.path.join(CONDA_BIN_PATH, 'gdal.dll')
        if os.path.exists(GDAL_LIBRARY_PATH):
            os.environ['GDAL_LIBRARY_PATH'] = GDAL_LIBRARY_PATH