# geoclient/api_urls.py
from rest_framework.routers import DefaultRouter
from .api import PointViewSet

router = DefaultRouter()
router.register(r'points', PointViewSet, basename='point')

urlpatterns = router.urls