# geoclient/admin.py
from django.contrib.gis import admin 
from .models import Point, UploadedRinexFile
from django.utils.html import format_html 
from django.urls import reverse 


@admin.register(Point)
class PointAdmin(admin.GISModelAdmin): # Теперь admin.GISModelAdmin будет найден
    list_display = ('name', 'timestamp', 'point_type', 'source_file_link', 'latitude', 'longitude')
    search_fields = ('name', 'description')
    list_filter = ('timestamp', 'point_type', 'source_file')
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 10,
            'default_lat': 55.75,
            'default_lon': 37.61,
        },
    }
    # fields = ('name', 'location', 'timestamp', 'description', 'point_type', 'source_file', 'raw_x', 'raw_y', 'raw_z')
    # readonly_fields = ('raw_x', 'raw_y', 'raw_z')

    def source_file_link(self, obj):
        if obj.source_file:
            link = reverse("admin:geoclient_uploadedrinexfile_change", args=[obj.source_file.id])
            return format_html('<a href="{}">{}</a>', link, obj.source_file.file.name.split('/')[-1])
        return "-"
    source_file_link.short_description = 'Исходный файл'


@admin.register(UploadedRinexFile)
class UploadedRinexFileAdmin(admin.ModelAdmin): # admin.ModelAdmin тоже будет работать
    list_display = ('file_name_display', 'uploaded_at', 'file_type', 'points_count_display')
    list_filter = ('uploaded_at', 'file_type')
    
    def file_name_display(self, obj):
        if obj.file and hasattr(obj.file, 'name'):
            return obj.file.name.split('/')[-1]
        return "Файл отсутствует"
    file_name_display.short_description = 'Имя файла'
    file_name_display.admin_order_field = 'file'

    def points_count_display(self, obj):
        if hasattr(obj, 'points'):
            return obj.points.count()
        return 0
    points_count_display.short_description = 'Кол-во точек'