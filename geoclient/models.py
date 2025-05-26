# geoclient/models.py
from django.contrib.gis.db import models as gis_models
from django.db import models

class UploadedRinexFile(models.Model):
    file = models.FileField(upload_to='rinex_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(max_length=10, blank=True, null=True, help_text="Тип файла (o, n, g)") # .25o, .25n, .25g
    remarks = models.TextField(blank=True, null=True, help_text="Заметки по файлу")

    def __str__(self):
        return f"{self.file.name} (загружен: {self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        verbose_name = "Загруженный RINEX файл"
        verbose_name_plural = "Загруженные RINEX файлы"
        ordering = ['-uploaded_at']


class Point(models.Model):
    name = models.CharField(max_length=255, help_text="Имя точки/маркера")
    location = gis_models.PointField(srid=4326, help_text="Координаты точки (WGS84)") # SRID 4326 это WGS84 (широта/долгота)
    timestamp = models.DateTimeField(null=True, blank=True, help_text="Время наблюдения")
    description = models.TextField(blank=True, null=True, help_text="Дополнительное описание")
    # Связь с исходным файлом, если точка была из него извлечена
    source_file = models.ForeignKey(
        UploadedRinexFile,
        on_delete=models.SET_NULL, # или models.CASCADE, если точки должны удаляться с файлом
        null=True,
        blank=True,
        related_name='points'
    )
    # Можно добавить другие поля, извлекаемые из RINEX
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
        return f"{self.name} ({self.location.x:.6f}, {self.location.y:.6f}) at {self.timestamp}"

    @property
    def latitude(self):
        return self.location.y

    @property
    def longitude(self):
        return self.location.x