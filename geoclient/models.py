# geoclient/models.py
from django.contrib.gis.db import models as gis_models
from django.db import models

class UploadedRinexFile(models.Model):
    file = models.FileField(upload_to='rinex_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True) 
    file_type = models.CharField(max_length=10, blank=True, null=True, help_text="Тип файла (o, n, g)")
    remarks = models.TextField(blank=True, null=True, help_text="Заметки по файлу")

    def __str__(self):
        # Безопасный вызов strftime
        uploaded_at_str = self.uploaded_at.strftime('%Y-%m-%d %H:%M') if self.uploaded_at else "N/A"
        file_name_str = self.file.name if self.file and hasattr(self.file, 'name') else "No file"
        return f"{file_name_str} (загружен: {uploaded_at_str})"

    class Meta:
        verbose_name = "Загруженный RINEX файл"
        verbose_name_plural = "Загруженные RINEX файлы"
        ordering = ['-uploaded_at']


class Point(models.Model):
    POINT_TYPES = [
        ('ggs', 'Пункты гос. геодезической сети'),
        ('ggs_kurgan', 'Пункты ГГС на курганах'),
        ('survey', 'Точки съемочной сети'),
        ('survey_kurgan', 'Точки съемочной сети на курганах'),
        ('astro', 'Астрономические пункты'),
        ('leveling', 'Нивелирные марки/реперы'),
        ('default', 'Неопределенный тип'),
    ]

    name = models.CharField(max_length=255, help_text="Имя точки/маркера")
    location = gis_models.PointField(srid=4326, help_text="Координаты точки (WGS84)")
    timestamp = models.DateTimeField(null=True, blank=True, help_text="Время наблюдения")
    description = models.TextField(blank=True, null=True, help_text="Дополнительное описание")
    
    point_type = models.CharField(
        max_length=20,
        choices=POINT_TYPES,
        default='default',
        help_text="Тип точки"
    )

    source_file = models.ForeignKey(
        UploadedRinexFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points'
    )
    raw_x = models.FloatField(null=True, blank=True, help_text="Исходная координата X (ECEF)")
    raw_y = models.FloatField(null=True, blank=True, help_text="Исходная координата Y (ECEF)")
    raw_z = models.FloatField(null=True, blank=True, help_text="Исходная координата Z (ECEF)")

    class Meta:
        verbose_name = "Точка на карте"
        verbose_name_plural = "Точки на карте"
        indexes = [
            gis_models.Index(fields=['location'], name='location_idx'),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        # Безопасное получение отображаемого имени типа
        type_display = self.get_point_type_display() if hasattr(self, 'get_point_type_display') else self.point_type
        return f"{self.name} ({type_display})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None