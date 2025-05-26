# geoclient/urls.py
from django.urls import path # <--- path ИМПОРТИРУЕТСЯ ЗДЕСЬ
from . import views 

app_name = 'geoclient'

urlpatterns = [
    path('', views.VueAppContainerView.as_view(), name='vue_app_main'),
    path('api/upload-rinex/', views.RinexUploadApiView.as_view(), name='api_upload_rinex'),
    
    # Путь для получения CSRF токена (если вы решите использовать этот метод)
    path('api/get-csrf-token/', views.get_csrf_token_view, name='get_csrf_token'), # <--- ОН ОПРЕДЕЛЯЕТСЯ ЗДЕСЬ
]