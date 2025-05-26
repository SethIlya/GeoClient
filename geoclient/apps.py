# geoclient/apps.py
from django.apps import AppConfig

class GeoclientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'geoclient' # Имя вашего приложения
    verbose_name = "ГеоКлиент" # Опционально, для админки