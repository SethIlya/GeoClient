# geoclient/models.py
from django.contrib.gis.db import models as gis_models
from django.db import models
from datetime import datetime # Убедимся, что datetime импортирован, если используется в методах

class UploadedRinexFile(models.Model):
    """
    Модель для хранения информации о загруженных RINEX файлах.
    """
    file = models.FileField(
        upload_to='rinex_files/', 
        verbose_name="Файл"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Время загрузки"
    ) 
    file_type = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        help_text="Тип файла (o, n, g, и т.д.)",
        verbose_name="Тип файла"
    )
    remarks = models.TextField(
        blank=True, 
        null=True, 
        help_text="Заметки или комментарии по файлу",
        verbose_name="Заметки"
    )

    def __str__(self):
        uploaded_at_str = self.uploaded_at.strftime('%Y-%m-%d %H:%M') if self.uploaded_at else "N/A"
        file_name_str = self.file.name.split('/')[-1] if self.file and hasattr(self.file, 'name') else "Файл отсутствует"
        return f"{file_name_str} (загружен: {uploaded_at_str})"

    class Meta:
        verbose_name = "Загруженный RINEX файл"
        verbose_name_plural = "Загруженные RINEX файлы"
        ordering = ['-uploaded_at']


class StationDirectoryName(models.Model):
    """
    Модель для хранения записей справочника имен станций.
    Эти имена пользователь может выбирать и присваивать точкам.
    """
    name = models.CharField(
        max_length=255, 
        unique=True,
        db_index=True,
        help_text="Уникальное имя станции из справочника (например, Вахим, База_1)",
        verbose_name="Имя станции в справочнике"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления записи")

    class Meta:
        verbose_name = "Запись справочника имен"
        verbose_name_plural = "Справочник имен станций"
        ordering = ['name']

    def __str__(self):
        return self.name


class Point(models.Model):
    """
    Модель для хранения информации о геодезических точках.
    """
    POINT_TYPES = [
        ('ggs', 'Пункты гос. геодезической сети'),
        ('ggs_kurgan', 'Пункты ГГС на курганах'),
        ('survey', 'Точки съемочной сети'),
        ('survey_kurgan', 'Точки съемочной сети на курганах'),
        ('astro', 'Астрономические пункты'),
        ('leveling', 'Нивелирные марки/реперы'),
        ('default', 'Неопределенный тип'),
    ]

    id = models.CharField(
        max_length=50,
        primary_key=True, 
        help_text="Идентификатор точки (обычно MARKER NAME из RINEX файла)",
        verbose_name="ID точки (Marker Name)"
    )
    station_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Присвоенное пользователем имя станции/пункта",
        verbose_name="Присвоенное имя станции"
    )
    location = gis_models.PointField(
        srid=4326,
        help_text="Географические координаты точки (долгота, широта в WGS84)",
        verbose_name="Местоположение"
    )
    timestamp = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Время наблюдения или создания записи",
        verbose_name="Время наблюдения"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Дополнительное описание или комментарии к точке",
        verbose_name="Описание"
    )
    point_type = models.CharField(
        max_length=20,
        choices=POINT_TYPES,
        default='default',
        help_text="Тип геодезического пункта или точки",
        verbose_name="Тип точки"
    )
    source_file = models.ForeignKey(
        UploadedRinexFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='points',
        verbose_name="Исходный RINEX файл"
    )
    raw_x = models.FloatField(null=True, blank=True, help_text="Исходная координата X (ECEF из RINEX)")
    raw_y = models.FloatField(null=True, blank=True, help_text="Исходная координата Y (ECEF из RINEX)")
    raw_z = models.FloatField(null=True, blank=True, help_text="Исходная координата Z (ECEF из RINEX)")
    receiver_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Номер приемника (REC # из RINEX)",
        verbose_name="Номер приемника"
    )
    antenna_height = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Измеренная высота антенны (компонента H из ANTENNA: DELTA H/E/N в RINEX, в метрах)",
        verbose_name="Высота антенны (H)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи точки")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления записи точки")

    class Meta:
        verbose_name = "Точка на карте"
        verbose_name_plural = "Точки на карте"
        indexes = [
            gis_models.Index(fields=['location'], name='location_idx'),
            models.Index(fields=['timestamp'], name='timestamp_idx'),
            models.Index(fields=['station_name'], name='station_name_idx'),
        ]
        ordering = ['id']

    def __str__(self):
        type_display = self.get_point_type_display()
        display_identifier = self.station_name if self.station_name else self.id
        return f"{display_identifier} (ID: {self.id}, Тип: {type_display})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None