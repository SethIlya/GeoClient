# geoclient/urls.py
from django.urls import path
from . import views 

app_name = 'geoclient'

urlpatterns = [
    path('', views.VueAppContainerView.as_view(), name='vue_app_main'),
    path('api/upload-rinex/', views.RinexUploadApiView.as_view(), name='api_upload_rinex'),
    # --- НОВЫЙ ПУТЬ ---
    path('api/upload-kml/', views.KMLUploadApiView.as_view(), name='api_upload_kml'),
    path('api/get-csrf-token/', views.get_csrf_token_view, name='get_csrf_token'),
]