# geoclient/api_urls.py
from django.urls import path
from . import views 
from rest_framework.routers import DefaultRouter
from .api import (
    PointViewSet,
    StationDirectoryNameViewSet,
    ObservationViewSet,
    LoginView,
    LogoutView,
    UserStatusView
)
from .views import RinexUploadApiView, KMLUploadApiView

router = DefaultRouter()
router.register(r'points', PointViewSet, basename='point')
router.register(r'station-names', StationDirectoryNameViewSet, basename='station-name')
router.register(r'observations', ObservationViewSet, basename='observation')

# Основные URL от роутера
urlpatterns = router.urls

# Дополнительные URL для конкретных действий
urlpatterns += [
    # API для файлов
    path('upload-rinex/', RinexUploadApiView.as_view(), name='api_upload_rinex'),
    path('upload-kml/', KMLUploadApiView.as_view(), name='api_upload_kml'),

    path('login/', LoginView.as_view(), name='api_login'),
    path('logout/', LogoutView.as_view(), name='api_logout'),
    path('user-status/', UserStatusView.as_view(), name='api_user_status'),
     path('get-csrf-token/', views.get_csrf_token_view, name='get_csrf_token'),
]