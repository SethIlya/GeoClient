# geoclient/models.py

import os
import re
import uuid
from django.contrib.gis.db import models as gis_models
from django.db import models

# --- НОВАЯ, БОЛЕЕ НАДЕЖНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ ПУТИ ---
def rinex_file_path(instance, filename):
    """
    Генерирует чистый и предсказуемый путь для сохранения RINEX файлов.
    Эта версия устойчива к случайным символам, добавляемым Django.
    Пример: из 'KAM32700_2_Abc123.20g' сделает 'rinex_files/KAM32700/KAM32700_2.20g'
    """

    name_part = re.sub(r'\.\d{2}[ogn]$', '', filename, flags=re.IGNORECASE)
    match = re.search(r'(\.\d{2}[ogn])$', filename, re.IGNORECASE)
    extension = match.group(1).lower() if match else os.path.splitext(filename)[1].lower()
    station_folder_name = re.split(r'[_ -]', name_part)[0].upper()
    clean_filename = f"{name_part}{extension}"
    return os.path.join('rinex_files', station_folder_name, clean_filename)


class UploadedRinexFile(models.Model):
    # Используем нашу новую функцию
    file = models.FileField(upload_to=rinex_file_path, verbose_name="Файл")
    file_hash = models.CharField(max_length=64, unique=True, db_index=True, blank=True, null=True, help_text="Хэш-сумма SHA-256")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Время загрузки")
    file_type = models.CharField(max_length=10, blank=True, null=True, verbose_name="Тип файла")
    remarks = models.TextField(blank=True, null=True, verbose_name="Заметки")
    upload_group = models.UUIDField(default=uuid.uuid4, db_index=True, null=True, blank=True, help_text="ID группы связанных файлов")

    def delete(self, *args, **kwargs):
        # Добавлена проверка на существование файла перед удалением
        if self.file and hasattr(self.file, 'path') and os.path.exists(self.file.path):
            self.file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return os.path.basename(self.file.name) if self.file else "Файл отсутствует"

    class Meta:
        verbose_name = "Загруженный RINEX файл"
        verbose_name_plural = "Загруженные RINEX файлы"
        ordering = ['-uploaded_at']


class StationDirectoryName(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True, help_text="Уникальное имя станции из справочника", verbose_name="Имя станции в справочнике")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Запись справочника имен"
        verbose_name_plural = "Справочник имен станций"
        ordering = ['name']

    def __str__(self):
        return self.name


class GeodeticPoint(models.Model):
    POINT_TYPES = [
        ('ggs', 'Пункты гос. геодезической сети'),
        ('ggs_kurgan', 'Пункты ГГС на курганах'),
        ('survey', 'Точки съемочной сети'),
        ('survey_kurgan', 'Точки съемочной сети на курганах'),
        ('astro', 'Астрономические пункты/Высокоточная сеть'),
        ('leveling', 'Нивелирная марка/ГНСС'),
        ('default', 'Неопределенный тип'),
    ]

    id = models.CharField(max_length=50, primary_key=True, help_text="Уникальный ID пункта (Marker Name из RINEX)", verbose_name="ID пункта")
    station_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Присвоенное имя станции")
    location = gis_models.PointField(srid=4326, verbose_name="Актуальное местоположение")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    point_type = models.CharField(max_length=20, choices=POINT_TYPES, default='default', verbose_name="Тип точки")
    network_class = models.CharField(max_length=255, blank=True, null=True, verbose_name="Класс сети")
    index_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Индекс (номенклатура)")
    center_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Тип центра")
    status = models.CharField(max_length=100, blank=True, null=True, verbose_name="Статус")
    mark_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Номер марки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Геодезический пункт"
        verbose_name_plural = "Геодезические пункты"
        indexes = [gis_models.Index(fields=['location'], name='geopoint_location_idx')]
        ordering = ['id']

    def __str__(self):
        display_identifier = self.station_name if self.station_name else self.id
        return f"Пункт: {display_identifier} (ID: {self.id})"


class Observation(models.Model):
    id = models.BigAutoField(primary_key=True)
    point = models.ForeignKey(GeodeticPoint, on_delete=models.CASCADE, related_name='observations', verbose_name="Геодезический пункт")
    location = gis_models.PointField(srid=4326, verbose_name="Местоположение наблюдения")
    timestamp = models.DateTimeField(verbose_name="Время наблюдения (первого)")
    source_file = models.ForeignKey(UploadedRinexFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations', verbose_name="Исходный RINEX файл")
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