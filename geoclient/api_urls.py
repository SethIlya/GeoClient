# geoclient/api_urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter
from .api import PointViewSet, StationDirectoryNameViewSet, ObservationViewSet
from . import views 

router = DefaultRouter()
router.register(r'points', PointViewSet, basename='point')
router.register(r'station-names', StationDirectoryNameViewSet, basename='station-name')
# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Регистрируем ViewSet для наблюдений ---
# Теперь будут доступны URL вида /api/observations/<id>/download/
router.register(r'observations', ObservationViewSet, basename='observation')

# Получаем все URL из роутера
urlpatterns = router.urls

# Добавляем остальные API-пути (для загрузки)
urlpatterns += [
    path('upload-rinex/', views.RinexUploadApiView.as_view(), name='api_upload_rinex'),
    path('upload-kml/', views.KMLUploadApiView.as_view(), name='api_upload_kml'),
    path('get-csrf-token/', views.get_csrf_token_view, name='get_csrf_token'),
]