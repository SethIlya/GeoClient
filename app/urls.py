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
# app/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Все API-запросы по-прежнему здесь
    path('api/', include('geoclient.api_urls')),
    
    # --- ИЗМЕНЕНИЕ: Мы УДАЛИЛИ отсюда re_path для /media/ ---
    
    # Все остальные запросы уходят во Vue-приложение (catch-all)
    path('', include('geoclient.urls')), 
]