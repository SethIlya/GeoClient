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
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('DB_NAME', 'Praktika'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '12345'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432'),
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
        "dev_mode": DEBUG,
        "dev_server_host": "127.0.0.1",
        "dev_server_port": 5173,
    }
}

# ==============================================================================
# СПЕЦИФИЧНЫЕ ДЛЯ СИСТЕМЫ НАСТРОЙКИ (GDAL)
# ==============================================================================
if platform.system() == 'Windows':
    # Твоя логика поиска пути была абсолютно верной.
    # Мы просто используем ее для прямого присваивания настроек Django.
    CONDA_BIN_PATH = BASE_DIR / '.conda' / 'Library' / 'bin'
    
    if CONDA_BIN_PATH.exists():
        print(f"INFO: Conda bin path for GDAL found at: {CONDA_BIN_PATH}")
        GDAL_DLL_PATH = CONDA_BIN_PATH / 'gdal.dll'
        
        if GDAL_DLL_PATH.exists():
            # Это самый надежный способ указать Django путь к библиотекам.
            GDAL_LIBRARY_PATH = str(GDAL_DLL_PATH)
            GEOS_LIBRARY_PATH = str(CONDA_BIN_PATH / 'geos_c.dll')
            PROJ_LIBRARY_PATH = str(CONDA_BIN_PATH / 'proj.dll')
            print(f"INFO: GDAL library path set to: {GDAL_LIBRARY_PATH}")
        else:
            print(f"WARNING: gdal.dll not found in {CONDA_BIN_PATH}. GeoDjango may fail.")
    else:
        # Если ты перенесешь проект на Linux/macOS или в Docker, этот блок не выполнится.
        print(f"WARNING: Windows-specific Conda path not found: {CONDA_BIN_PATH}. Assuming non-Windows environment.")



# ==============================================================================
# НАСТРОЙКИ ЗАГРУЗКИ ФАЙЛОВ
# ==============================================================================

# Создаем папку tmp внутри проекта, чтобы не использовать системный tmpfs (который маленький)
TEMP_UPLOAD_DIR = BASE_DIR / 'tmp_uploads'
if not TEMP_UPLOAD_DIR.exists():
    TEMP_UPLOAD_DIR.mkdir(exist_ok=True)

# Говорим Django использовать эту папку для временных файлов при загрузке
FILE_UPLOAD_TEMP_DIR = str(TEMP_UPLOAD_DIR)

# Если файл больше 2.5MB, он будет стримиться на диск (в нашу папку), а не в память.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB