"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# app/urls.py (полный путь C:\Users\iimin\DJANGO_PRAKTIK\app\urls.py)

from django.contrib import admin
from django.urls import path, include # Убедитесь, что include импортирован
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Подключаем все URL из geoclient/urls.py
    # Все пути из geoclient/urls.py будут доступны от корня сайта (например, /api/upload-rinex/)
    path('', include('geoclient.urls')), 
    
    # Подключаем URL для DRF API точек (если используется)
    # Они будут доступны по префиксу /api/ (например, /api/points/)
    # Убедитесь, что 'geoclient.api_urls' существует и настроен, если раскомментируете
    path('api/', include('geoclient.api_urls')), 

    # Если бы вы хотели, чтобы все URL из geoclient.urls имели префикс, например, /map/:
    # path('map/', include('geoclient.urls')),
    # Тогда URL для загрузки был бы /map/api/upload-rinex/
]

# Это для раздачи медиа-файлов (загруженных RINEX) в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Раздача статических файлов (собранного Vue) обычно обрабатывается Django автоматически
    # в DEBUG режиме, если STATIC_URL и STATICFILES_DIRS настроены,
    # или веб-сервером (Nginx) в production.
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Обычно не требуется для runserver