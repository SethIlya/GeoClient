# geoclient/admin.py

from django.contrib.gis import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

# Импортируем ВСЕ ваши модели
from .models import GeodeticPoint, Observation, UploadedRinexFile, StationDirectoryName

# --- 1. Класс для отображения наблюдений ВНУТРИ карточки точки ---
# Этот класс будет использоваться как "встраиваемый" в админку GeodeticPoint
class ObservationInline(admin.TabularInline):
    """
    Позволяет просматривать и редактировать наблюдения прямо со страницы 
    их "родительской" геодезической точки.
    """
    model = Observation  # Указываем, с какой моделью работаем
    extra = 0  # Не показывать пустые формы для добавления новых наблюдений
    
    # Поля, которые будут отображаться в таблице наблюдений
    fields = ('timestamp', 'location', 'receiver_number', 'antenna_height', 'source_file_link')
    
    # Делаем все поля только для чтения, т.к. они создаются из файлов
    readonly_fields = ('timestamp', 'location', 'receiver_number', 'antenna_height', 'source_file_link')

    # Создаем кастомное поле со ссылкой на исходный файл
    def source_file_link(self, obj):
        if obj.source_file:
            link = reverse("admin:geoclient_uploadedrinexfile_change", args=[obj.source_file.pk])
            # Отображаем только имя файла, а не полный путь
            filename = obj.source_file.file.name.split('/')[-1]
            return format_html('<a href="{}">{}</a>', link, filename)
        return "–"
    source_file_link.short_description = 'Исходный файл'
    
    # Отключаем возможность добавлять/изменять/удалять наблюдения через этот инлайн,
    # так как они должны создаваться только при загрузке файлов.
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        # Можно разрешить удаление, если это необходимо
        return True

# --- 2. Настройки админки для основной модели GeodeticPoint ---
@admin.register(GeodeticPoint)
class GeodeticPointAdmin(admin.GISModelAdmin):
    """
    Настройки админ-панели для модели геодезических пунктов.
    """
    # Отображаем только те поля, которые реально существуют в модели GeodeticPoint
    list_display = ('id', 'station_name', 'point_type', 'observation_count', 'updated_at')
    
    # Поля для поиска
    search_fields = ('id', 'station_name', 'description')
    
    # Поля для фильтрации
    list_filter = ('point_type', 'updated_at')
    
    # Подключаем наш инлайн, чтобы видеть наблюдения на странице точки
    inlines = [ObservationInline]

    # Делаем системные поля только для чтения
    readonly_fields = ('id', 'created_at', 'updated_at')

    # Метод для подсчета и сортировки по количеству наблюдений
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(_observation_count=Count('observations'))

    @admin.display(description='Кол-во наблюдений', ordering='_observation_count')
    def observation_count(self, obj):
        return obj._observation_count

# --- 3. Настройки админки для модели UploadedRinexFile ---
@admin.register(UploadedRinexFile)
class UploadedRinexFileAdmin(admin.ModelAdmin):
    # В list_display используем поля из самой модели или кастомные методы
    list_display = ('file_name_display', 'uploaded_at', 'file_type', 'observations_count_display')
    list_filter = ('uploaded_at', 'file_type')
    readonly_fields = ('uploaded_at', 'file_hash')
    date_hierarchy = 'uploaded_at'
    search_fields = ('file', 'file_hash')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Считаем связанные наблюдения для каждого файла
        queryset = queryset.annotate(_observations_count=Count('observations', distinct=True))
        return queryset

    # Метод для красивого отображения имени файла
    @admin.display(description='Имя файла', ordering='file')
    def file_name_display(self, obj):
        if obj.file and hasattr(obj.file, 'name'):
            return obj.file.name.split('/')[-1]
        return "Файл отсутствует"

    # Метод для отображения количества связанных наблюдений
    @admin.display(description='Кол-во наблюдений', ordering='_observations_count')
    def observations_count_display(self, obj):
        return obj._observations_count

# --- 4. Настройки админки для справочника имен ---
@admin.register(StationDirectoryName)
class StationDirectoryNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'