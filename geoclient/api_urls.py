# geoclient/api_urls.py
from rest_framework.routers import DefaultRouter
from .api import PointViewSet, StationDirectoryNameViewSet # Добавляем новый ViewSet

router = DefaultRouter()
router.register(r'points', PointViewSet, basename='point')
router.register(r'station-names', StationDirectoryNameViewSet, basename='station-name') # Новый маршрут

urlpatterns = router.urls