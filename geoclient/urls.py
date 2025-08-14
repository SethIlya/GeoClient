# geoclient/urls.py

from django.urls import path
from . import views 

app_name = 'geoclient'

urlpatterns = [
    # Этот путь-перехватчик (`catch-all`) должен быть единственным.
    # Он отдает наш "умный" index.html для любого запроса, который не является /admin/ или /api/.
    path('', views.VueAppContainerView.as_view(), name='vue_app_main'),
]