# geoclient/models.py

from django.contrib.gis.db import models as gis_models
from django.db import models
from datetime import datetime

class UploadedRinexFile(models.Model):
    """
    Модель для хранения информации о загруженных RINEX файлах.
    """
    file = models.FileField(
        upload_to='rinex_files/',
        verbose_name="Файл"
    )
    file_hash = models.CharField(
        max_length=64, # Длина для хэша SHA-256
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        help_text="Хэш-сумма SHA-256 содержимого файла для определения дубликатов."
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

    def delete(self, *args, **kwargs):
        """
        Переопределяем стандартный метод delete.
        Сначала удаляем связанный файл с диска, затем саму запись в БД.
        """
        if self.file:
            self.file.delete(save=False)
        
        super().delete(*args, **kwargs)

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


class GeodeticPoint(models.Model):
    """
    Модель, представляющая физический геодезический пункт на местности.
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
        help_text="Уникальный ID пункта (Marker Name из RINEX)",
        verbose_name="ID пункта"
    )
    station_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Присвоенное имя станции")
    location = gis_models.PointField(srid=4326, verbose_name="Актуальное местоположение")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    point_type = models.CharField(max_length=20, choices=POINT_TYPES, default='default', verbose_name="Тип точки")
    network_class = models.CharField(max_length=255, blank=True, null=True, verbose_name="Класс сети")
    index_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Индекс (номенклатура)")
    center_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Тип центра")
    status = models.CharField(max_length=100, blank=True, null=True, verbose_name="Статус")
    mark_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Номер марки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления записи")

    class Meta:
        verbose_name = "Геодезический пункт"
        verbose_name_plural = "Геодезические пункты"
        indexes = [gis_models.Index(fields=['location'], name='geopoint_location_idx')]
        ordering = ['id']

    def __str__(self):
        display_identifier = self.station_name if self.station_name else self.id
        return f"Пункт: {display_identifier} (ID: {self.id})"


class Observation(models.Model):
    """
    Модель, представляющая одно конкретное измерение/наблюдение.
    """
    id = models.BigAutoField(primary_key=True)
    point = models.ForeignKey(GeodeticPoint, on_delete=models.CASCADE, related_name='observations', verbose_name="Геодезический пункт")
    location = gis_models.PointField(srid=4326, verbose_name="Местоположение наблюдения")
    timestamp = models.DateTimeField(verbose_name="Время наблюдения (первого)")
    source_file = models.ForeignKey(UploadedRinexFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations', verbose_name="Исходный RINEX файл")
    
    # --- ИЗМЕНЕНИЕ: Добавляем поле для длительности ---
    duration = models.DurationField(null=True, blank=True, verbose_name="Длительность наблюдения")
    
    raw_x = models.FloatField(null=True, blank=True, help_text="Исходная координата X (ECEF из RINEX)")
    raw_y = models.FloatField(null=True, blank=True, help_text="Исходная координата Y (ECEF из RINEX)")
    raw_z = models.FloatField(null=True, blank=True, help_text="Исходная координата Z (ECEF из RINEX)")
    receiver_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Номер приемника")
    antenna_height = models.FloatField(null=True, blank=True, help_text="Высота антенны (H) из RINEX", verbose_name="Высота антенны (H)")
    
    class Meta:
        verbose_name = "Наблюдение"
        verbose_name_plural = "Наблюдения"
        unique_together = ('point', 'timestamp')
        ordering = ['-timestamp']

    def __str__(self):
        return f"Наблюдение для {self.point.id} в {self.timestamp.strftime('%Y-%m-%d %H:%M')}"