# geoclient/admin.py
from django.contrib.gis import admin
from .models import Point, UploadedRinexFile, StationDirectoryName
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count


@admin.register(Point)
class PointAdmin(admin.GISModelAdmin):
    list_display = (
        'id',               # CharField, бывшее имя/MARKER NAME
        'station_name',     # Новое поле
        'timestamp',
        'point_type',
        'source_file_link', # Метод этого класса
        'latitude',         # @property из модели Point
        'longitude',        # @property из модели Point
        'receiver_number',  # Новое поле из модели Point
        'antenna_height',   # Новое поле из модели Point
        'updated_at'        # Новое поле из модели Point
    )
    search_fields = (
        'id',
        'station_name',
        'description',
        'receiver_number'
    )
    list_filter = (
        'point_type', 
        'timestamp', 
        'source_file', 
        'updated_at' # Поле из модели Point
    )
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 10,
            'default_lat': 55.75,
            'default_lon': 37.61,
        },
    }
    # Поля, отображаемые в форме редактирования/создания в админке
    fields = (
        'id', 
        'station_name', 
        'location', 
        'timestamp', 
        'description', 
        'point_type', 
        'source_file', 
        'raw_x', 'raw_y', 'raw_z', 
        'receiver_number', 
        'antenna_height',
        ('created_at', 'updated_at') # Отображаем даты создания/обновления в одной строке
    )
    
    # Поля, которые будут только для чтения в форме редактирования
    # ID (MARKER NAME) генерируется из файла и является PK, не должен меняться.
    # raw_x, raw_y, raw_z, receiver_number, antenna_height - также из файла.
    # created_at, updated_at - устанавливаются автоматически Django.
    readonly_fields_on_edit = ('id', 'raw_x', 'raw_y', 'raw_z', 'receiver_number', 'antenna_height', 'created_at', 'updated_at')
    readonly_fields_on_add = ('raw_x', 'raw_y', 'raw_z', 'receiver_number', 'antenna_height', 'created_at', 'updated_at') # ID можно задать при создании вручную

    def get_readonly_fields(self, request, obj=None):
        if obj: # При редактировании существующего объекта
            return self.readonly_fields_on_edit
        # При создании нового объекта (obj is None)
        return self.readonly_fields_on_add

    def source_file_link(self, obj):
        if obj.source_file:
            # UploadedRinexFile.pk должен быть стандартным auto-increment id
            link = reverse("admin:geoclient_uploadedrinexfile_change", args=[obj.source_file.pk]) 
            return format_html('<a href="{}">{}</a>', link, obj.source_file.file.name.split('/')[-1])
        return "-"
    source_file_link.short_description = 'Исходный файл'
    source_file_link.admin_order_field = 'source_file__file' # Позволяет сортировку по имени файла


@admin.register(UploadedRinexFile)
class UploadedRinexFileAdmin(admin.ModelAdmin):
    list_display = ('file_name_display', 'uploaded_at', 'file_type', 'points_count_display')
    list_filter = ('uploaded_at', 'file_type')
    readonly_fields = ('uploaded_at',) # Время загрузки не меняется
    date_hierarchy = 'uploaded_at' # Удобная навигация по датам
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(_points_count=Count('points', distinct=True)) # distinct=True на всякий случай
        return queryset

    def file_name_display(self, obj):
        if obj.file and hasattr(obj.file, 'name'):
            return obj.file.name.split('/')[-1]
        return "Файл отсутствует"
    file_name_display.short_description = 'Имя файла'
    file_name_display.admin_order_field = 'file'

    def points_count_display(self, obj):
        return obj._points_count
    points_count_display.short_description = 'Кол-во точек'
    points_count_display.admin_order_field = '_points_count'

@admin.register(StationDirectoryName)
class StationDirectoryNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'