# geoclient/api_urls.py
from rest_framework.routers import DefaultRouter
from .api import PointViewSet # Предполагается, что у вас есть geoclient/api.py с PointViewSet

router = DefaultRouter()
router.register(r'points', PointViewSet, basename='point') # basename='point' используется для reverse('point-list')

urlpatterns = router.urls